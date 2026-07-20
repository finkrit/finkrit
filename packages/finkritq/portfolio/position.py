# finkrit/packages/finkritq/portfolio/position.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finkritq.asset import Asset
from finkritq.portfolio.taxlot import TaxLot


@dataclass(slots=True, eq=False)
class Position:
    """
    A position in a single asset: the asset plus its tax lots. Part of the
    one-directional tree (owned by a Portfolio; does not point back up to it).

    ``eq=False`` -> identity equality. A Position is a mutable entity
    (``last_price`` is updated in place), not a value; two distinct positions
    are never "equal" just because their contents match, and value-equality on
    a mutable entity is a footgun (it also used to recurse through the old
    Position<->TaxLot cycle).
    """

    id: str
    asset: Asset
    lots: tuple[TaxLot, ...]

    notes: str | None = None
    last_price: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.lots:
            raise ValueError("Position requires at least one lot.")

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

    def is_long_term(self, as_of: date) -> bool:
        return all(lot.is_long_term(as_of) for lot in self.lots)

    def __len__(self) -> int:
        return self.lot_count

    def __str__(self) -> str:
        return f"{self.asset.ticker} ({self.quantity})"

    def __repr__(self) -> str:
        return (f"Position(asset={self.asset.ticker!r}, quantity={self.quantity}, lots={self.lot_count})")
    
