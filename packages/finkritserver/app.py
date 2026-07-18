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
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder

from finagent.assistant import Assistant
from finagent.store import AssetNotFoundError, PortfolioNotFoundError

from finkritserver.portfolio import build_portfolio
from finkritserver.schemas import (
    AskRequest,
    AskResponse,
    PortfolioRegistered,
    PortfolioSpec,
    PortfolioSummary,
)


def create_app(assistant: Assistant) -> FastAPI:
    app = FastAPI(title="finkrit", version="0.1.0")

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

    @app.get("/api/portfolio/{portfolio_id}/report")
    def report(portfolio_id: str, metrics: str = "core") -> dict:
        # Deterministic, no LLM. Sync handler -> FastAPI threadpools the
        # blocking data fetch + numpy math off the event loop.
        try:
            result = assistant.report(portfolio_id, metrics)
        except (PortfolioNotFoundError, AssetNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            # bad metric selector, etc.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return jsonable_encoder(result)

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest) -> AskResponse:
        answer = await assistant.ask_async(req.question)
        return AskResponse(answer=answer)

    return app
