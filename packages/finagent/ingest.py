# finagent/ingest.py
"""
Portfolio extraction from a CSV upload, in code first and by model second.

``parse_portfolio_csv_in_code`` maps the file with the alias tables below and
answers on its own when the header names all four fields we need. That is the
common case, a broker export or our own sample, and it is instant, free, and
identical whatever model is configured. It returns None when it cannot be
sure, which is the only time the file reaches an LLM.

``parse_portfolio_csv`` is that fallback: the raw text handed to the model in
one shot (pydantic-ai structured output, output_type=ParsedPortfolio), which
maps whatever columns, order, and date format the file happens to have.
Flagship models parse a CSV fine on their own. A local one does too, but
slowly enough that a user watches a blank screen for minutes and concludes the
app is broken, which is what put the deterministic path in front of it.

Either way, anything guessed or normalized comes back as a `warning` or a
holding's `confidence_note` for the user to review and correct in the UI,
rather than being silently absorbed.

This is deliberately NOT committed to the Store: both functions only return
the extracted shape. The caller (finkritserver) shows it to the user for
correction, then registers it via the existing portfolio-registration path
once confirmed.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent, models

# The name a parse carries when the caller has nothing better. The upload
# endpoint passes the file's own name, so this is the fallback for a direct
# caller with only text in hand.
DEFAULT_PORTFOLIO_NAME = "Uploaded portfolio"

# Column names a real export uses for the four fields we need. The lists grow
# every time a new spelling turns up, and they are the contract for whether a
# file loads without a model, so a name missing here is not a cosmetic gap.
#
# The cost list is per share only. A total cost column is deliberately absent,
# since dividing it needs the quantity and the header names sit too close
# together ("Cost Per Share" next to "Cost Basis Total") to risk guessing
# wrong. A file that offers only a total is exactly the ambiguity the model
# fallback exists for.
CSV_ALIASES: dict[str, tuple[str, ...]] = {
    "ticker": ("ticker", "symbol"),
    "quantity": ("quantity", "shares", "qty", "units"),
    "cost_per_share": (
        "cost_per_share", "cost per share", "cost/share", "cost basis / share",
        "cost basis per share", "price per share", "cost basis", "avg cost",
        "average cost basis", "cost", "price", "price paid",
    ),
    "acquired": ("acquired", "date acquired", "purchase date", "date"),
}

# Accepted date layouts, in the order they are tried. "iso" is YYYY-MM-DD.
CSV_DATE_FORMATS: tuple[str, ...] = ("iso", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y")


def csv_value(row: dict, field: str) -> str | None:
    """The value in ``row`` for one of our fields, by any of its aliases.

    Header names are matched case and space insensitively, since an export
    writes "Date Acquired" and a hand edited file writes "date acquired".
    """
    lowered = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
    for name in CSV_ALIASES[field]:
        if lowered.get(name):
            return lowered[name]
    return None


def csv_date(value: str | None) -> date | None:
    """``value`` as a date, or None when no accepted layout fits.

    None rather than a fallback date, so each caller decides what an
    unreadable date means. The CLI substitutes a default and carries on, the
    upload path records it as something the user should look at.
    """
    if not value:
        return None
    for fmt in CSV_DATE_FORMATS:
        try:
            if fmt == "iso":
                return date.fromisoformat(value)
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def csv_number(value: str | None, default: str = "0") -> str:
    """``value`` as plain numeric text, presentation stripped.

    Real exports format money rather than writing bare numbers: "$1,234.56", a
    trailing space, sometimes parentheses for a negative. Returned as a string
    so a caller wanting exactness can hand it straight to Decimal.
    """
    if not value:
        return default
    cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return cleaned or default


def csv_header_covers_every_field(fieldnames) -> bool:
    """Whether this header names all four fields under a known alias.

    The gate on answering without a model. All four present means every value
    comes from a column the file labelled, with nothing inferred from position
    or filled in from a default, and a model would only be re-reading what the
    header already said. One missing means real ambiguity, which is the case
    the model is there for.
    """
    if not fieldnames:
        return False
    lowered = {(name or "").strip().lower() for name in fieldnames}
    return all(
        any(alias in lowered for alias in aliases)
        for aliases in CSV_ALIASES.values()
    )

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


def parse_portfolio_csv_in_code(
    csv_text: str,
    name: str = DEFAULT_PORTFOLIO_NAME,
) -> ParsedPortfolio | None:
    """``csv_text`` mapped without a model, or None when that is not safe.

    None means "ask the model", and it is returned for a header that does not
    name all four fields, and for a file that yields no usable row at all. An
    empty result is not an answer, and letting it through would turn a file we
    failed to read into a portfolio the user appears to have emptied.

    Everything short of that is handled here rather than deferred. A blank or
    unreadable cell under a column that does exist gets a stand in value and a
    confidence_note naming what happened, which is the review surface the UI
    already renders. A model would not recover the missing value either, and
    the honest move is to show the gap rather than spend two minutes having it
    guessed.

    One row is one tax lot, never merged. A ticker bought three times stays
    three rows, because the separate lots are the whole basis of the tax
    analytics downstream.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not csv_header_covers_every_field(reader.fieldnames):
        return None

    holdings: list[ParsedHolding] = []
    skipped = 0
    for row in reader:
        ticker = csv_value(row, "ticker")
        if not ticker:
            # A blank line, a totals row, a disclaimer footer. Counted rather
            # than dropped in silence, since a file that is mostly skipped is
            # a file we read wrong.
            skipped += 1
            continue

        notes: list[str] = []
        quantity = csv_value(row, "quantity")
        if quantity is None:
            notes.append("quantity was blank, filled in as 0")
        cost = csv_value(row, "cost_per_share")
        if cost is None:
            notes.append("cost per share was blank, filled in as 0")

        acquired = csv_date(csv_value(row, "acquired"))
        if acquired is None:
            # Today keeps the lot short term, which is the conservative read:
            # it never claims a long term rate the holding has not earned.
            notes.append("acquired date was missing or unreadable, filled in as today")
            acquired = date.today()

        holdings.append(
            ParsedHolding(
                ticker=ticker.upper(),
                quantity=float(csv_number(quantity)),
                cost_per_share=float(csv_number(cost)),
                acquired=acquired,
                confidence_note="; ".join(notes) if notes else None,
            )
        )

    if not holdings:
        return None

    warnings: list[str] = []
    if skipped:
        warnings.append(f"{skipped} row(s) had no ticker and were skipped.")
    return ParsedPortfolio(name=name, holdings=holdings, warnings=warnings)


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
