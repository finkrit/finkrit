# finkrit/packages/finkritq/portfolio/taxlot.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxLot:
    """
    A single tax lot: a quantity of an asset acquired at a point in time and
    price. A pure value object and the atomic unit tax-lot analytics (harvesting,
    realized/unrealized gains, holding period) operate on. It does NOT reference
    its parent Position (the tree is one-directional Portfolio -> Position ->
    TaxLot); the asset it belongs to is known by the owning Position, so a lot
    carries only what a lot intrinsically is. Frozen: a tax lot is an immutable
    historical record.

    Time-relative queries (holding period, long/short-term) take an explicit
    `as_of` date rather than reading the wall clock, so a lot gives the same
    answer for a given reference date and nothing here depends on "now". The
    "acquired is not in the future" check likewise belongs at the ingestion
    boundary (where the as-of date is known), not in the value object, since
    "future" has no meaning without a reference date.
    """

    id: str

    quantity: Decimal
    cost_per_share: Decimal
    acquired: date

    notes: str | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive.")

        if self.cost_per_share <= 0:
            raise ValueError("cost_per_share must be positive.")

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.cost_per_share

    def holding_period(self, as_of: date) -> timedelta:
        return as_of - self.acquired

    def holding_days(self, as_of: date) -> int:
        return self.holding_period(as_of).days

    def is_long_term(self, as_of: date) -> bool:
        return self.holding_days(as_of) >= 365

    def __str__(self) -> str:
        return f"TaxLot({self.quantity} @ {self.cost_per_share})"

    def __repr__(self) -> str:
        return (
            f"TaxLot("
            f"quantity={self.quantity}, "
            f"cost_per_share={self.cost_per_share}, "
            f"acquired={self.acquired!r})"
        )

    def market_value(self, last_price: Decimal) -> Decimal:
        return self.quantity * last_price

    def unrealized_gain(self, last_price: Decimal) -> Decimal:
        return self.market_value(last_price) - self.cost_basis

    def unrealized_return(self, last_price: Decimal) -> Decimal:
        if self.cost_per_share == 0:
            return Decimal("0")
        return (last_price - self.cost_per_share) / self.cost_per_share
