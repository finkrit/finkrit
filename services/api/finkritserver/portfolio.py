# finkritserver/portfolio.py
"""
Builds a finkritq Portfolio from a flat PortfolioSpec.

The wire format is deliberately flat, one row per tax lot, because that is the
shape a brokerage export actually has: buy the same ticker five times and the
file has five rows. Rows are grouped by asset here, so those five become one
Position holding five TaxLots.

That grouping is what makes the tax analytics work. finkritq's lot functions
operate on a Position's lots, so harvesting and lot selection can only weigh the
alternatives when every lot for a ticker sits under one Position. Emitting a
Position per row would leave each holding looking like a single blended lot,
with nothing to choose between.

finq's Portfolio is a lean set of Positions with no accounts, custodian, or
tax-org structure. That ownership graph belongs to the proprietary layer, not to
risk and performance analysis.
"""
from __future__ import annotations

from decimal import Decimal

from finkritq.asset import Stock
from finkritq.datatype import Currency, Exchange
from finkritq.portfolio import Portfolio, Position, TaxLot

from finkritserver.schemas import HoldingSpec, PortfolioSpec


def _make_stock(holding: HoldingSpec) -> Stock:
    return Stock(
        ticker=holding.ticker,
        currency=Currency(holding.currency),
        exchange=Exchange(holding.exchange),
        company_name=holding.ticker,
    )


def _asset_key(holding: HoldingSpec) -> tuple[str, str, str]:
    # Two rows are lots of the same holding only if they are the same
    # instrument. The same ticker on a different exchange or in a different
    # currency is not.
    return (holding.ticker, holding.exchange, holding.currency)


def _group_by_asset(
    holdings: list[HoldingSpec],
) -> dict[tuple[str, str, str], list[HoldingSpec]]:
    # Insertion ordered, so positions come back in the order the file listed
    # them rather than alphabetically or arbitrarily.
    grouped: dict[tuple[str, str, str], list[HoldingSpec]] = {}
    for holding in holdings:
        grouped.setdefault(_asset_key(holding), []).append(holding)
    return grouped


def _make_position(rows: list[HoldingSpec], index: int) -> Position:
    first = rows[0]
    lots = tuple(
        TaxLot(
            # Unique within the position. The ticker alone is no longer enough,
            # now that one position can hold several lots.
            id=f"lot-{first.ticker}-{lot_index}",
            quantity=Decimal(str(row.quantity)),
            cost_per_share=Decimal(str(row.cost_per_share)),
            acquired=row.acquired,
        )
        for lot_index, row in enumerate(rows)
    )
    return Position(id=f"pos-{first.ticker}-{index}", asset=_make_stock(first), lots=lots)


def build_portfolio(spec: PortfolioSpec) -> Portfolio:
    grouped = _group_by_asset(spec.holdings)
    return Portfolio(
        id=spec.id,
        name=spec.name,
        positions=[
            _make_position(rows, index) for index, rows in enumerate(grouped.values())
        ],
    )
