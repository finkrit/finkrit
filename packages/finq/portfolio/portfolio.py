# finkrit/packages/finq/portfolio/portfolio.py

from __future__ import annotations

from datetime import date

import numpy as np
from numpy.typing import NDArray

from packages.finq.asset import Asset
from packages.finq.asset.lot import Lot
from packages.finq.portfolio.position import Position


class Portfolio:
    """
    A collection of positions.
    """

    def __init__(self, positions: list[Position]):
        self._positions = positions

    @property
    def positions(self) -> tuple[Position, ...]:
        return tuple(self._positions)

    @property
    def assets(self) -> tuple[Asset, ...]:
        return tuple(
            position.asset
            for position in self.positions
        )

    @property
    def lots(self) -> tuple[Lot, ...]:
        return tuple(
            lot
            for position in self.positions
            for lot in position.lots
        )

    @property
    def quantities(self) -> NDArray[np.float64]:
        return np.asarray(
            [position.quantity for position in self.positions],
            dtype=np.float64,
        )

    @property
    def quantity(self) -> float:
        return sum(
            position.quantity
            for position in self.positions
        )

    @property
    def cost_basis(self) -> float:
        return sum(
            position.cost_basis
            for position in self.positions
        )

    @property
    def n_positions(self) -> int:
        return len(self.positions)

    @property
    def n_assets(self) -> int:
        return len(self.assets)

    @property
    def n_lots(self) -> int:
        return len(self.lots)

    @property
    def long_term_lots(self) -> tuple[Lot, ...]:
        return tuple(
            lot
            for lot in self.lots
            if lot.is_long_term
        )

    @property
    def short_term_lots(self) -> tuple[Lot, ...]:
        return tuple(
            lot
            for lot in self.lots
            if not lot.is_long_term
        )

    @property
    def long_term_quantity(self) -> float:
        return sum(
            lot.quantity
            for lot in self.long_term_lots
        )

    @property
    def short_term_quantity(self) -> float:
        return sum(
            lot.quantity
            for lot in self.short_term_lots
        )

    @property
    def earliest_acquired(self) -> date:
        return min(
            lot.acquired
            for lot in self.lots
        )

    @property
    def latest_acquired(self) -> date:
        return max(
            lot.acquired
            for lot in self.lots
        )

    def add_position(self, position: Position) -> None:
        """
        Add a position to the portfolio.
        """
        self._positions.append(position)

    def __len__(self) -> int:
        return self.n_positions

    def __iter__(self):
        return iter(self._positions)

    def __getitem__(self, index: int) -> Position:
        return self._positions[index]

    def __repr__(self) -> str:
        return (
            f"Portfolio("
            f"{self.n_positions} positions, "
            f"{self.n_assets} assets, "
            f"{self.n_lots} lots)"
        )
    
    