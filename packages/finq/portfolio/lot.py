from dataclasses import dataclass
from datetime import date, timedelta

from packages.finq.asset import Asset


@dataclass(frozen=True, slots=True)
class Lot:
    """
    A tax lot representing shares acquired together at the same cost basis.
    """

    asset: Asset
    quantity: float
    cost_per_share: float
    acquired: date

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be positive.")

        if self.cost_per_share <= 0:
            raise ValueError("cost_per_share must be positive.")
        
        if self.acquired > date.today():
            raise ValueError("acquired cannot be in the future.")   

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.cost_per_share
    
    @property
    def holding_period(self) -> timedelta:
        """
        Time elapsed since the lot was acquired.
        """
        return date.today() - self.acquired


    @property
    def age(self) -> int:
        """
        Holding period in days.
        """
        return self.holding_period.days


    @property
    def is_long_term(self) -> bool:
        """
        Whether the lot qualifies as a long-term holding.
        """
        return self.age >= 365

    def market_value(self, last_price: float) -> float:
        return self.quantity * last_price

    def unrealized_pnl(self, last_price: float) -> float:
        return self.market_value(last_price) - self.cost_basis

    def unrealized_return(self, last_price: float) -> float:
        if self.cost_per_share == 0:
            return 0.0

        return (last_price - self.cost_per_share) / self.cost_per_share
    
    