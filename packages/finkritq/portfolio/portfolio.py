# finkrit/packages/finkritq/portfolio/portfolio.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterator

from finkritq.asset import Asset
from finkritq.portfolio.position import Position
from finkritq.portfolio.taxlot import TaxLot


@dataclass(slots=True)
class Portfolio:
    """
    A set of positions analyzed together -- the quant analysis unit.

    This is deliberately lean: just a bag of positions, with no notion of who
    owns it, where it custodies, or how it is taxed. The ownership/legal graph
    (household, registration, account, custodian) lives above finq, in the RIA
    layer, which flattens an account's or a household's holdings *down to* a
    Portfolio to run analytics. finq never sees an account -- it sees positions
    and prices. "Portfolio" here is the polymorphic analysis view: whatever set
    of holdings you point the measures at.
    """

    id: str
    name: str

    positions: list[Position] = field(default_factory=list)

    notes: str | None = None

    # ------------------------------------------------------------------
    # Position Management
    # ------------------------------------------------------------------

    def add_position(self, position: Position) -> Position:
        existing = self.get_position(position.id)

        if existing is not None:
            # Idempotent for the same object; a *different* position claiming an
            # existing id is a conflict we surface rather than silently drop.
            if existing is position:
                return existing
            raise ValueError(f"A position with id '{position.id}' already exists.")

        self.positions.append(position)
        return position

    def remove_position(self, position_id: str) -> Position | None:
        position = self.get_position(position_id)

        if position is None:
            return None

        self.positions.remove(position)
        return position

    def get_position(self, position_id: str) -> Position | None:
        return next((p for p in self.positions if p.id == position_id), None)

    def has_position(self, position_id: str) -> bool:
        return self.get_position(position_id) is not None

    # ------------------------------------------------------------------
    # Derived Collections
    # ------------------------------------------------------------------

    @property
    def assets(self) -> tuple[Asset, ...]:
        return tuple(position.asset for position in self.positions)

    @property
    def lots(self) -> tuple[TaxLot, ...]:
        return tuple(
            lot
            for position in self.positions
            for lot in position.lots
        )

    # ------------------------------------------------------------------
    # Aggregate Properties
    # ------------------------------------------------------------------

    @property
    def cost_basis(self) -> Decimal:
        return sum((position.cost_basis for position in self.positions), start=Decimal("0"))

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    @property
    def lot_count(self) -> int:
        return len(self.lots)

    @property
    def is_empty(self) -> bool:
        return not self.positions

    def long_term_lots(self, as_of: date) -> tuple[TaxLot, ...]:
        return tuple(lot for lot in self.lots if lot.is_long_term(as_of))

    def short_term_lots(self, as_of: date) -> tuple[TaxLot, ...]:
        return tuple(lot for lot in self.lots if not lot.is_long_term(as_of))

    @property
    def earliest_acquired(self) -> date:
        return min(lot.acquired for lot in self.lots)

    @property
    def latest_acquired(self) -> date:
        return max(lot.acquired for lot in self.lots)

    # ------------------------------------------------------------------
    # Collection Interface
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[Position]:
        return iter(self.positions)

    def __len__(self) -> int:
        return len(self.positions)

    def __contains__(self, position: Position) -> bool:
        return position in self.positions

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (
            f"Portfolio("
            f"name={self.name!r}, "
            f"positions={self.position_count})"
        )
