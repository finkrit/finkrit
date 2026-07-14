# finkrit/packages/finq/portfolio/lot.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.finq.asset import Asset
    from packages.finq.portfolio.account import Account
    from packages.finq.portfolio.position import Position


@dataclass(slots=True)
class Lot:
    """
    Represents a single tax lot within a position.
    """

    id: str
    position: Position

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
    def asset(self) -> Asset:
        return self.position.asset

    @property
    def account(self) -> Account:
        return self.position.account

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

