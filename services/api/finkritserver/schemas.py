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

from finkritcore.store import DEFAULT_PORTFOLIO_ID


class HoldingSpec(BaseModel):
    """One tax lot: a ticker with a quantity, a cost basis, and the date it was
    acquired.

    One row is one lot, not one holding. Repeat a ticker to describe a position
    built from several purchases, which is how a brokerage export reads and what
    the tax analytics need in order to have lots to choose between.
    `portfolio.build_portfolio` groups rows by instrument into a single Position.

    Ownership details (custodian, account, registration) are omitted, since they
    are irrelevant to risk and performance analysis and belong to the
    proprietary layer, not finq."""

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
    # Omit on the first message and the server starts a thread and returns its
    # id. Send that id back on later messages to keep the context, which is what
    # makes a follow-up like "and how does that compare?" work.
    conversation_id: str | None = None


class SpecialistAnswer(BaseModel):
    """One specialist's own reply, before it was folded into the combined answer."""

    name: str        # risk, performance, optimization, tax
    question: str    # the sub-question the orchestrator handed it
    answer: str      # what it returned, verbatim


class AskResponse(BaseModel):
    answer: str
    # Always populated, including for a request that omitted it. The client
    # stores it and echoes it back on the next question.
    conversation_id: str
    # Which specialists answered, in call order (risk, performance, optimization,
    # tax), deduped. The UI shows these as pills so a user can see which domains
    # were consulted rather than take a combined answer on faith. Empty when the
    # orchestrator answered without delegating.
    specialists: list[str] = []
    # The same fan out with each specialist's verbatim reply, read off the run
    # rather than off the final text. Lets the UI show the work: open the
    # disclosure and see exactly what the tax specialist said, and check the
    # combined answer against it. Not deduped, since one specialist asked two
    # different sub-questions gave two different answers.
    specialist_answers: list[SpecialistAnswer] = []
