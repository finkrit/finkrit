# # finkrit/packages/finq/portfolio/portfoliosnapshot.py
from dataclasses import dataclass, field

from packages.finq.asset import Asset, AssetSnapshot
from packages.finq.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """
    A point-in-time market valuation of a portfolio.
    """

    portfolio: Portfolio
    _snapshots: dict[Asset, AssetSnapshot] = field(repr=False)

    def snapshot(self, asset: Asset) -> AssetSnapshot:
        return self._snapshots[asset]

    def __getitem__(self, asset: Asset) -> AssetSnapshot:
        return self._snapshots[asset]

    @property
    def market_value(self) -> float:
        return sum(
            position.quantity * self[position.asset].last_price
            for position in self.portfolio.positions
        )

    @property
    def cost_basis(self) -> float:
        return sum(
            position.quantity * position.average_cost
            for position in self.portfolio.positions
            if position.average_cost is not None
        )

    @property
    def unrealized_pnl(self) -> float | None:
        if any(p.average_cost is None for p in self.portfolio.positions):
            return None

        return self.market_value - self.cost_basis

    @property
    def daily_pnl(self) -> float:
        return sum(
            (
                self[position.asset].last_price
                - self[position.asset].previous_close
            ) * position.quantity
            for position in self.portfolio.positions
        )