# finkritserver/app.py
"""
FastAPI layer over a finagent Assistant.

`create_app(assistant)` is a factory so tests can inject an Assistant backed by
a fake model + fake registry (no network, no API key). The real entrypoint
(the `finkrit chat` CLI, later) will build a live Assistant and pass it in.

Endpoint topology mirrors finagent's two surfaces:
  - /report is deterministic -> a plain `def` handler, which FastAPI runs in a
    threadpool, so the blocking risk math never stalls the event loop.
  - /ask is the LLM path -> an `async def` handler awaiting assistant.ask_async.

Also serves the built Svelte SPA (see private/webapp_plan.md) and enables CORS
for local dev, so `finkrit chat` can be one process while the Svelte dev
server is developed against it separately.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from finagent.assistant import Assistant
from finagent.report import PortfolioRiskReport
from finagent.store import AssetNotFoundError, PortfolioNotFoundError

from finkritserver.portfolio import build_portfolio
from finkritserver.schemas import (
    AskRequest,
    AskResponse,
    PortfolioRegistered,
    PortfolioSpec,
    PortfolioSummary,
)

# Default dev origins: Vite's default port, both localhost/127.0.0.1 spellings
# (browsers don't treat them as the same origin). This is a local, single-user
# tool, not a multi-tenant service, so a fixed allowlist of local dev origins
# is the right default -- override for a different Vite port or a real deploy.
DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

# Where the built Svelte SPA lands (npm run build -> copied in at publish/CI
# time, per private/webapp_plan.md). Doesn't exist until Phase 3 -- the API
# still runs standalone if this directory is absent.
DEFAULT_STATIC_DIR: Path = Path(__file__).parent / "static"


def create_app(
    assistant: Assistant,
    *,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
    static_dir: Path | None = DEFAULT_STATIC_DIR,
) -> FastAPI:
    app = FastAPI(title="finkrit", version="0.1.0")

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

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest) -> AskResponse:
        answer = await assistant.ask_async(req.question)
        return AskResponse(answer=answer)

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
