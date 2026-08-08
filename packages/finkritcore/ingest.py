# finkritcore/ingest.py
"""
Portfolio extraction from a CSV upload, in code.

``parse_portfolio_csv_in_code`` maps the file with the alias tables below and
answers on its own when the header names all four fields we need. That is the
common case, a broker export or our own sample, and it is instant, free, and
needs no model, no key, and no network. It returns None when it cannot be
sure, which is the only time the file has to reach an LLM at all. That
fallback lives in ``finagent.ingest``, one layer up, because it is the only
part of reading a CSV that needs an agent framework.

Anything guessed or normalized comes back as a portfolio ``warning`` or a
holding's ``confidence_note`` for the user to review and correct in the UI,
rather than being silently absorbed.

This is deliberately NOT committed to the Store: the function only returns the
extracted shape. The caller (finkritserver or any other) shows it to the user for
correction, then registers it via the existing portfolio-registration path
once confirmed.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

from pydantic import BaseModel, Field

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
    # Enrichment, not a requirement. A real export names the security next to
    # its symbol and we used to drop it, storing "AAPL Corp" while the file
    # said "APPLE INC". A model handed a ticker with no name supplies one from
    # memory, and one observed run turned V into "Vanguard Utilities ETF" (it
    # is Visa). Reading a column already in front of us removes the reason to
    # invent, which beats catching the invention afterwards.
    "name": ("description", "name", "security", "security name", "company", "company name"),
}

# The four a file must label for us to read it without a model. `name` is
# deliberately absent: it improves an answer, it does not make one possible,
# and requiring it would push every file that lacks it back to an LLM.
REQUIRED_CSV_FIELDS: tuple[str, ...] = ("ticker", "quantity", "cost_per_share", "acquired")

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
        any(alias in lowered for alias in CSV_ALIASES[field])
        for field in REQUIRED_CSV_FIELDS
    )


class ParsedHolding(BaseModel):
    ticker: str
    # The security's own name when the file gave one. None rather than a
    # manufactured "{ticker} Corp", which reads like a real name and is not.
    name: str | None = None
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
                name=csv_value(row, "name"),
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
