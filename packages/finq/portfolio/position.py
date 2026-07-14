# finkrit/packages/finq/portfolio/position.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from packages.finq.asset import Asset
from packages.finq.portfolio.lot import Lot

if TYPE_CHECKING:
    from packages.finq.portfolio.account import Account


@dataclass(slots=True)
class Position:
    """
    Represents a position in a single asset within an account.
    """

    id: str
    account: Account
    asset: Asset
    lots: tuple[Lot, ...]

    notes: str | None = None
    last_price: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.lots:
            raise ValueError("Position requires at least one lot.")

        if any(lot.asset != self.asset for lot in self.lots):
            raise ValueError("All lots must belong to the same asset.")

    @property
    def quantity(self) -> Decimal:
        return sum((lot.quantity for lot in self.lots), start=Decimal("0"))

    @property
    def cost_basis(self) -> Decimal:
        return sum((lot.cost_basis for lot in self.lots), start=Decimal("0"))

    @property
    def market_value(self) -> Decimal:
        if self.last_price is None:
            return self.cost_basis
        return self.quantity * self.last_price

    @property
    def unrealized_gain(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def average_cost(self) -> Decimal:
        return Decimal("0") if self.quantity == 0 else self.cost_basis / self.quantity

    @property
    def lot_count(self) -> int:
        return len(self.lots)

    @property
    def earliest_acquired(self) -> date:
        return min(lot.acquired for lot in self.lots)

    @property
    def latest_acquired(self) -> date:
        return max(lot.acquired for lot in self.lots)

    @property
    def is_long_term(self) -> bool:
        return all(lot.is_long_term for lot in self.lots)

    def __len__(self) -> int:
        return self.lot_count

    def __str__(self) -> str:
        return f"{self.asset.ticker} ({self.quantity})"

    def __repr__(self) -> str:
        return (f"Position(asset={self.asset.ticker!r}, quantity={self.quantity}, lots={self.lot_count})")
    
