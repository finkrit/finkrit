# finagent/ingest.py
"""
The model fallback for a CSV upload we could not read in code.

``finkritcore.ingest.parse_portfolio_csv_in_code`` handles any file whose
header names the ticker, quantity, cost per share, and acquired date. Only
when it returns None does the raw text come here, to be handed to the model in
one shot (pydantic-ai structured output, output_type=ParsedPortfolio), which
maps whatever columns, order, and date format the file happens to have.

Flagship models parse a CSV fine on their own. A local one does too, but
slowly enough that a user watches a blank screen for minutes and concludes the
app is broken, which is what put the deterministic path in front of this one.
``Assistant.parse_portfolio_csv`` is where the two are sequenced.

Like the deterministic path, this returns the extracted shape and commits
nothing to the Store.
"""
from __future__ import annotations

from pydantic_ai import Agent, models

# Re-exported because they are this module's own return types: a caller
# awaiting parse_portfolio_csv needs ParsedPortfolio, and finkritcore is where
# the shape is defined now that the mapper that fills it lives there.
from finkritcore.ingest import (
    DEFAULT_PORTFOLIO_NAME,
    ParsedHolding,
    ParsedPortfolio,
    parse_portfolio_csv_in_code,
)

__all__ = [
    "INGEST_INSTRUCTIONS",
    "parse_portfolio_csv",
    "parse_portfolio_csv_async",
    "ParsedPortfolio",
    "ParsedHolding",
    "DEFAULT_PORTFOLIO_NAME",
    "parse_portfolio_csv_in_code",
]

INGEST_INSTRUCTIONS = (
    "You extract portfolio holdings from raw CSV text pasted below. Columns "
    "vary in name and order (e.g. 'Symbol'/'Ticker', 'Shares'/'Quantity', "
    "'Avg Cost'/'Cost Basis'/'Price Paid', 'Purchase Date'/'Date Acquired'). "
    "Map each row to: ticker, quantity, cost_per_share (cost basis PER SHARE, "
    "not total), acquired (ISO date). Only include exchange/currency if the "
    "file states them; otherwise omit and let the default apply. "
    "One output row is one TAX LOT, not one holding. When a ticker appears on "
    "several rows, because it was bought more than once, emit every row and keep "
    "each purchase date and cost separate. Never merge them into a single row "
    "or average their cost, since the separate lots are what tax-loss "
    "harvesting and lot selection operate on. "
    "Do not invent holdings that aren't in the data. If a value is missing, "
    "ambiguous, or you had to guess/normalize it (e.g. total cost divided "
    "into per-share, an inferred year, an inferred exchange), say so in that "
    "holding's confidence_note or as a portfolio-level warning -- the user "
    "reviews and corrects these before anything is saved."
)


def parse_portfolio_csv(
    csv_text: str,
    model: models.Model | models.KnownModelName | str,
) -> ParsedPortfolio:
    """``csv_text`` mapped by the model. The fallback, not the front door.

    Callers should try ``parse_portfolio_csv_in_code`` first, which is what
    ``Assistant.parse_portfolio_csv`` does. This stays model only so its cost
    is never hidden: reaching it means the file really was ambiguous.
    """
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
