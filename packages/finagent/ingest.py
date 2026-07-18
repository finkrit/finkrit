# finagent/ingest.py
"""
LLM-based portfolio extraction from an arbitrary CSV upload.

No tabular-parsing library needed: the raw file text is handed straight to
the model (a one-shot pydantic-ai structured-output call, output_type=
ParsedPortfolio) and it maps whatever columns/order/date-format the file has
onto our schema. Flagship models parse CSVs fine on their own; anything
genuinely ambiguous comes back as a `warning`/`confidence_note` for the user
to review and correct in the UI, rather than the model silently guessing.

This is deliberately NOT committed to the Store -- parse_portfolio_csv()
only returns the extracted shape. The caller (finkritserver) shows it to the
user for correction, then registers it via the existing portfolio-registration
path once confirmed.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field
from pydantic_ai import Agent, models

INGEST_INSTRUCTIONS = (
    "You extract portfolio holdings from raw CSV text pasted below. Columns "
    "vary in name and order (e.g. 'Symbol'/'Ticker', 'Shares'/'Quantity', "
    "'Avg Cost'/'Cost Basis'/'Price Paid', 'Purchase Date'/'Date Acquired'). "
    "Map each row to: ticker, quantity, cost_per_share (cost basis PER SHARE, "
    "not total), acquired (ISO date). Only include exchange/currency if the "
    "file states them; otherwise omit and let the default apply. "
    "Do not invent holdings that aren't in the data. If a value is missing, "
    "ambiguous, or you had to guess/normalize it (e.g. total cost divided "
    "into per-share, an inferred year, an inferred exchange), say so in that "
    "holding's confidence_note or as a portfolio-level warning -- the user "
    "reviews and corrects these before anything is saved."
)


class ParsedHolding(BaseModel):
    ticker: str
    quantity: float
    cost_per_share: float
    acquired: date
    exchange: str = "NASDAQ"
    currency: str = "USD"
    confidence_note: str | None = None


class ParsedPortfolio(BaseModel):
    name: str
    holdings: list[ParsedHolding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def parse_portfolio_csv(
    csv_text: str,
    model: models.Model | models.KnownModelName | str,
) -> ParsedPortfolio:
    agent = Agent(model, output_type=ParsedPortfolio, instructions=INGEST_INSTRUCTIONS)
    result = agent.run_sync(csv_text)
    return result.output


async def parse_portfolio_csv_async(
    csv_text: str,
    model: models.Model | models.KnownModelName | str,
) -> ParsedPortfolio:
    agent = Agent(model, output_type=ParsedPortfolio, instructions=INGEST_INSTRUCTIONS)
    result = await agent.run(csv_text)
    return result.output
