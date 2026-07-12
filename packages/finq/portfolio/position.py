from dataclasses import dataclass
from datetime import date

from packages.finq.asset import Asset
from packages.finq.asset.lot import Lot


@dataclass(frozen=True, slots=True)
class Position:
    """
    A position representing all open lots of a single asset.
    """

    asset: Asset
    lots: tuple[Lot, ...]

    def __post_init__(self):
        if not self.lots:
            raise ValueError("Position requires at least one lot.")

        if any(lot.asset != self.asset for lot in self.lots):
            raise ValueError("All lots must belong to the same asset.")

    @property
    def quantity(self) -> float:
        return sum(lot.quantity for lot in self.lots)

    @property
    def cost_basis(self) -> float:
        return sum(lot.cost_basis for lot in self.lots)

    @property
    def average_cost(self) -> float:
        return self.cost_basis / self.quantity

    @property
    def n_lots(self) -> int:
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

    def market_value(self, last_price: float) -> float:
        return self.quantity * last_price

    def unrealized_pnl(self, last_price: float) -> float:
        return self.market_value(last_price) - self.cost_basis

    def unrealized_return(self, last_price: float) -> float:
        return self.unrealized_pnl(last_price) / self.cost_basis

    def __len__(self) -> int:
        return self.n_lots

    def __repr__(self) -> str:
        return (f"Position({self.asset.ticker}, {self.quantity:g} shares, {self.n_lots} lots)")
    
    