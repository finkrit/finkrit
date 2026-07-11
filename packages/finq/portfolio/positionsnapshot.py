# finkrit/packages/finq/portfolio/positionsnapshot.py
from dataclasses import dataclass

from packages.finq.portfolio import Position


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    position: Position

    last_price: float
    previous_close: float

    @property
    def market_value(self) -> float:
        return self.position.quantity * self.last_price

    @property
    def cost_basis(self) -> float | None:
        if self.position.average_cost is None:
            return None
        return self.position.quantity * self.position.average_cost

    @property
    def unrealized_pnl(self) -> float | None:
        if self.position.average_cost is None:
            return None

        return self.market_value - self.cost_basis

    @property
    def daily_pnl(self) -> float:
        return (
            self.last_price - self.previous_close
        ) * self.position.quantity