# finkrit/packages/finkritq/portfolio/lot.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Lot:
    """
    A single tax lot: a quantity of an asset acquired at a point in time and
    price. A pure value object -- it does NOT reference its parent Position
    (the tree is one-directional Portfolio -> Account -> Position -> Lot). The
    asset/account it belongs to are known by the owning Position, so a Lot
    carries only what a lot intrinsically is. Frozen: a tax lot is an
    immutable historical record.
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

        if self.acquired > date.today():
            raise ValueError("acquired cannot be in the future.")

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.cost_per_share

    @property
    def holding_period(self) -> timedelta:
        return date.today() - self.acquired

    @property
    def holding_days(self) -> int:
        return self.holding_period.days

    @property
    def is_long_term(self) -> bool:
        return self.holding_days >= 365

    def __str__(self) -> str:
        return f"Lot({self.quantity} @ {self.cost_per_share})"

    def __repr__(self) -> str:
        return (
            f"Lot("
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

