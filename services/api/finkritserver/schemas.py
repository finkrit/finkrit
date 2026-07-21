# finkritserver/schemas.py
"""
HTTP boundary types (pydantic). Deliberately separate from finagent's internal
dataclasses: these are the JSON contract the Svelte frontend talks to, and an
LLM/user supplies primitives (tickers, quantities), never live domain objects.

Request models describe a portfolio in the flattest terms a UI can post;
`portfolio.build_portfolio` turns them into the finkritq object graph.
Responses are thin, the deterministic report is returned as-is via FastAPI's
encoder, so it is not re-modelled here.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from finagent.store import DEFAULT_PORTFOLIO_ID


class HoldingSpec(BaseModel):
    """One line item in a portfolio: a ticker with a quantity and a cost basis.
    Ownership details (custodian, account, registration) are omitted, since they
    are irrelevant to risk and performance analysis and belong to the RIA layer,
    not finq. One tax lot per holding for now (v1). Revisit if tax-lot features
    need per-lot detail within a single request."""

    ticker: str
    quantity: float = Field(gt=0)
    cost_per_share: float = Field(gt=0)
    acquired: date
    exchange: str = "NASDAQ"
    currency: str = "USD"


class PortfolioSpec(BaseModel):
    # Optional: the product is scoped to a single portfolio right now, so the
    # frontend doesn't need to invent/track an id -- omitting it defaults to
    # DEFAULT_PORTFOLIO_ID, the same id the risk agent's chat instructions
    # assume. Still overridable for tests or a future multi-portfolio UI.
    id: str = DEFAULT_PORTFOLIO_ID
    name: str
    holdings: list[HoldingSpec] = Field(min_length=1)


class PortfolioRegistered(BaseModel):
    portfolio_id: str


class PortfolioSummary(BaseModel):
    """Lightweight portfolio listing for the UI selector (no holdings)."""

    id: str
    name: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str
