# finkritserver/app.py
"""
FastAPI layer over a finagent Assistant.

`create_app(assistant)` is a factory so tests can inject an Assistant backed by
a fake model + fake registry (no network, no API key). The real entrypoint
(the `finkrit chat` CLI, later) will build a live Assistant and pass it in.

Endpoint topology mirrors finagent's two surfaces:
  - /report, /tax/signals, and /rebalance/compare are deterministic -> plain
    `def` handlers, which FastAPI runs in a threadpool, so the blocking math
    never stalls the event loop. No LLM anywhere in these paths: the dashboard
    reads code, chat reads the model.
  - /ask is the LLM path -> an `async def` handler awaiting assistant.ask_async.

Also serves the built Svelte SPA (see private/webapp_plan.md) and enables CORS
for local dev, so `finkrit chat` can be one process while the Svelte dev
server is developed against it separately.
"""
from __future__ import annotations

from pathlib import Path

import asyncio
import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic_ai.exceptions import AgentRunError

from finkritq.datatype import LotSaleMethod

from finkritcore.ingest import DEFAULT_PORTFOLIO_NAME, ParsedPortfolio
from finkritcore.report import PortfolioRiskReport, TaxSignalsReport
from finkritcore.report.tax_signals import (
    DEFAULT_COUNTDOWN_DAYS,
    DEFAULT_LONG_TERM_RATE,
    DEFAULT_SHORT_TERM_RATE,
)
from finkritcore.store import AssetNotFoundError, PortfolioNotFoundError

from finagent.assistant import Assistant
from finagent.progress import Step, StepDetail, progress_handler

from finkritserver.conversations import ConversationRegistry
from finkritserver.portfolio import build_portfolio
from finkritserver.schemas import (
    AskRequest,
    AskResponse,
    SpecialistAnswer,
    PortfolioRegistered,
    PortfolioSpec,
    PortfolioSummary,
)


# A CSV this large is almost certainly not "my brokerage holdings" -- fed
# whole into the model prompt, so cap it rather than send something
# pathological (or expensive) through.
MAX_UPLOAD_BYTES = 512_000  # 500 KB

# Default dev origins: Vite's default port, both localhost/127.0.0.1 spellings
# (browsers don't treat them as the same origin). This is a local, single-user
# tool, not a multi-tenant service, so a fixed allowlist of local dev origins
# is the right default -- override for a different Vite port or a real deploy.
DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

# Where the built Svelte SPA lands (npm run build -> copied in at publish/CI
# time, per private/webapp_plan.md). Doesn't exist until Phase 3 -- the API
# still runs standalone if this directory is absent.
DEFAULT_STATIC_DIR: Path = Path(__file__).parent / "static"

# How much each streamed progress step carries. FULL adds the arguments a tool
# was called with and each specialist's answer, which is what makes a live step
# readable rather than a bare name. This is the owner's own dashboard, so the
# payload is data they already receive at the end of the run. Drop to
# StepDetail.SUMMARY to stop sending either.
STREAM_DETAIL = StepDetail.FULL


def _frame(payload: dict) -> str:
    """One server sent event. Separated by a blank line, which is what tells a
    reader the frame is complete."""
    return f"data: {json.dumps(payload)}\n\n"


def _step_payload(step: Step) -> dict:
    # Enums as their values, so the wire format survives a member being
    # reordered (the reason those enums carry explicit strings at all).
    return {
        "kind": step.kind.value,
        "status": step.status.value,
        "name": step.name,
        "detail": step.detail,
        "call_id": step.call_id,
        "args": dict(step.args),
        "content": step.content,
    }


def create_app(
    assistant: Assistant,
    *,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
    static_dir: Path | None = DEFAULT_STATIC_DIR,
) -> FastAPI:
    app = FastAPI(title="finkrit", version="0.1.0")

    # One registry per app, holding the live chat threads keyed by conversation
    # id. Bounded and in memory, see finkritserver.conversations.
    conversations = ConversationRegistry(assistant)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/portfolio", response_model=PortfolioRegistered)
    def register_portfolio(spec: PortfolioSpec) -> PortfolioRegistered:
        assistant.register_portfolio(build_portfolio(spec))
        return PortfolioRegistered(portfolio_id=spec.id)

    @app.post("/api/portfolio/upload", response_model=ParsedPortfolio)
    async def upload_portfolio(file: UploadFile = File(...)) -> ParsedPortfolio:
        # Parse-only: an LLM extraction, NOT a registration. The frontend shows
        # the result for the user to review/correct, then submits the
        # (possibly corrected) holdings to POST /api/portfolio to commit --
        # re-registering the same id overwrites, so "upload a new file"
        # already replaces the single portfolio with no separate delete step.
        if file.filename and not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Only .csv uploads are supported right now.",
            )

        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({len(raw)} bytes, max {MAX_UPLOAD_BYTES}).",
            )

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.") from exc

        # The file's own name, so a parse that never reaches a model still
        # comes back named something the user recognizes rather than a
        # constant. The model path names it from the contents and ignores this.
        name = Path(file.filename).stem if file.filename else DEFAULT_PORTFOLIO_NAME
        return await assistant.parse_portfolio_csv_async(text, name)

    @app.get("/api/portfolios", response_model=list[PortfolioSummary])
    def list_portfolios() -> list[PortfolioSummary]:
        # Feeds the dashboard's portfolio selector.
        return [PortfolioSummary(id=p.id, name=p.name) for p in assistant.list_portfolios()]

    @app.get("/api/portfolio/{portfolio_id}/report", response_model=PortfolioRiskReport)
    def report(portfolio_id: str, metrics: str = "core") -> PortfolioRiskReport:
        # Deterministic, no LLM. Sync handler -> FastAPI threadpools the
        # blocking data fetch + numpy math off the event loop.
        # response_model=PortfolioRiskReport (a plain finagent dataclass, not
        # a pydantic model): FastAPI/Pydantic v2 generates a real, fully-typed
        # OpenAPI schema from it directly -- no need to duplicate the report
        # shape into a separate pydantic mirror here. This is the one that
        # matters most for a generated TypeScript client, since it's what the
        # whole dashboard renders off.
        try:
            return assistant.report(portfolio_id, metrics)
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            # bad metric selector, etc.
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/portfolio/{portfolio_id}/prefetch")
    def prefetch(portfolio_id: str) -> StreamingResponse:
        # Server-sent events: one line per ticker as its download completes,
        # so the dashboard can show which stocks are in flight instead of a
        # blank wait. Downloads run in parallel behind the stream. The 404
        # check happens here, before streaming starts, because a status code
        # cannot be changed once the response body has begun.
        try:
            events = assistant.prefetch_events(portfolio_id)
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        def stream():
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            # SSE must not be buffered by intermediaries or the per-ticker
            # progress arrives as one lump at the end.
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/portfolio/{portfolio_id}/tax/signals", response_model=TaxSignalsReport)
    def tax_signals(
        portfolio_id: str,
        short_term_rate: float = DEFAULT_SHORT_TERM_RATE,
        long_term_rate: float = DEFAULT_LONG_TERM_RATE,
        countdown_days: int = DEFAULT_COUNTDOWN_DAYS,
    ) -> TaxSignalsReport:
        # Deterministic, no LLM, same shape rules as /report: a plain frozen
        # dataclass FastAPI serializes directly. Rates are query params so the
        # dashboard can re-price the signals to the owner's actual brackets
        # without a redeploy.
        try:
            return assistant.tax_signals(
                portfolio_id,
                short_term_rate=short_term_rate,
                long_term_rate=long_term_rate,
                countdown_days=countdown_days,
            )
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            # inverted rate spread, bad thresholds
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/portfolio/{portfolio_id}/rebalance/compare")
    def rebalance_compare(
        portfolio_id: str,
        objective: str = "min_variance",
        gain_budget: float | None = None,
        tolerance: float = 0.02,
        method: str = LotSaleMethod.HIFO.value,
    ) -> dict:
        # Deterministic, no LLM. The same intel binding the chat compare tool
        # runs, so the drift budget card and a chat answer about the same
        # portfolio can never disagree. Returns the binding's dict as-is
        # (strategy rows keyed full / band_edge / partial_fill).
        try:
            lot_method = LotSaleMethod(method)
        except ValueError as exc:
            valid = ", ".join(m.value for m in LotSaleMethod)
            raise HTTPException(
                status_code=400,
                detail=f"Unknown lot method {method!r}. Use one of: {valid}.",
            ) from exc
        try:
            return assistant.rebalance_compare(
                portfolio_id,
                objective=objective,
                gain_budget=gain_budget,
                tolerance=tolerance,
                method=lot_method,
            )
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            # unknown objective, negative budget, degenerate price data
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest) -> AskResponse:
        # Threaded through a Conversation so follow-up questions keep their
        # context. The thread runs the orchestrator rather than a single
        # specialist: the dashboard takes free-form questions spanning risk,
        # performance, allocation, and tax, so it must reach every specialist.
        # A bare specialist would dead-end on anything outside its own domain.
        conversation_id, thread = conversations.get_or_create(req.conversation_id)
        try:
            answer = await thread.ask_async(req.question)
            fan_out = getattr(thread, "last_specialists", [])
            return AskResponse(
                answer=answer,
                conversation_id=conversation_id,
                specialists=getattr(thread, "last_specialist_names", []),
                specialist_answers=[
                    SpecialistAnswer(name=s.name, question=s.question, answer=s.answer)
                    for s in fan_out
                ],
            )
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except AgentRunError as exc:
            # The run could not complete: an LLM or provider error, a usage limit,
            # or a tool that kept failing past its retries. Return a clean 502
            # instead of a raw traceback, so the dashboard can show a message.
            raise HTTPException(
                status_code=502,
                detail=f"The assistant could not complete the request: {exc}",
            ) from exc

    @app.post("/api/ask/stream")
    async def ask_stream(req: AskRequest) -> StreamingResponse:
        # Same question as /api/ask, answered over a stream so the fan out is
        # visible while it happens rather than arriving all at once at the end.
        # Frames are {"type": "step"|"answer"|"error"}.
        #
        # Errors are frames, not status codes: the 404 and 502 that /api/ask
        # returns are raised from inside the run, by which point the response
        # has already begun and the status line is spent. A client must read
        # the stream to learn a question failed.
        conversation_id, thread = conversations.get_or_create(req.conversation_id)

        async def stream():
            # The agent run and the reader are concurrent: steps are pushed
            # from inside the run, which does not return until the answer is
            # complete. put_nowait on an unbounded queue so reporting progress
            # can never block the run that is producing it.
            queue: asyncio.Queue = asyncio.Queue()
            done = object()

            async def run() -> AskResponse:
                try:
                    answer = await thread.ask_async(
                        req.question,
                        event_handler=progress_handler(queue.put_nowait, STREAM_DETAIL),
                    )
                    return AskResponse(
                        answer=answer,
                        conversation_id=conversation_id,
                        specialists=getattr(thread, "last_specialist_names", []),
                        specialist_answers=[
                            SpecialistAnswer(name=s.name, question=s.question, answer=s.answer)
                            for s in getattr(thread, "last_specialists", [])
                        ],
                    )
                finally:
                    queue.put_nowait(done)

            task = asyncio.create_task(run())
            while True:
                item = await queue.get()
                if item is done:
                    break
                yield _frame({"type": "step", **_step_payload(item)})

            try:
                yield _frame({"type": "answer", **(await task).model_dump()})
            except (PortfolioNotFoundError, AssetNotFoundError) as exc:
                yield _frame({"type": "error", "detail": str(exc)})
            except AgentRunError as exc:
                yield _frame({
                    "type": "error",
                    "detail": f"The assistant could not complete the request: {exc}",
                })

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/ask/{conversation_id}/reset", status_code=204)
    def reset_conversation(conversation_id: str) -> None:
        # Start over without reloading the page. Unknown ids are a no-op, since
        # the desired end state (no history under that id) already holds.
        conversations.reset(conversation_id)

    # Registered last: FastAPI/Starlette match routes in registration order,
    # so the literal /api/* routes above always match before this catch-all
    # is ever consulted -- it only sees requests nothing above claimed.
    if static_dir is not None:
        _mount_spa(app, Path(static_dir))

    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """
    Serves the built Svelte SPA: a real file (JS/CSS/image) is returned as-is;
    any other GET path falls back to index.html so client-side routes (e.g.
    /dashboard) work on a hard refresh or deep link, not just navigation
    inside the SPA.

    Hand-rolled rather than `StaticFiles(html=True)`: that mode serves
    index.html for "/" and real directories, but 404s on an unknown SPA route
    like /dashboard (verified empirically) -- exactly the case a deep link
    needs. Building this explicitly means adding the security check
    `StaticFiles` gets for free: `full_path` is attacker-controlled input, so
    `static_dir / full_path` must be verified to still resolve inside
    `static_dir` before ever being read, or `../../etc/passwd`-style path
    traversal serves arbitrary files off disk.
    """
    resolved_root = static_dir.resolve()
    index_html = static_dir / "index.html"

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        candidate = (static_dir / full_path).resolve()
        is_within_root = candidate == resolved_root or resolved_root in candidate.parents
        if is_within_root and candidate.is_file():
            return FileResponse(candidate)
        if index_html.is_file():
            return FileResponse(index_html)
        raise HTTPException(
            status_code=404,
            detail="UI not built. Run the Svelte build, or pass static_dir=None to run API-only.",
        )
