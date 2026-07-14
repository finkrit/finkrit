# finkrit/packages/finq/portfolio/portfoliosnapshot.py
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

    def items(self):
        return self._snapshots.items()

    @property
    def market_value(self) -> float:
        return sum(
            position.market_value(self[position.asset].last_price)
            for position in self.portfolio.positions
        )

    @property
    def cost_basis(self) -> float:
        return sum(
            position.cost_basis
            for position in self.portfolio.positions
        )

    @property
    def unrealized_pnl(self) -> float:
        return sum(
            position.unrealized_pnl(self[position.asset].last_price)
            for position in self.portfolio.positions
        )

    @property
    def unrealized_return(self) -> float:
        if self.cost_basis == 0:
            return 0.0

        return self.unrealized_pnl / self.cost_basis

    @property
    def daily_pnl(self) -> float:
        return sum(
            (
                self[position.asset].last_price
                - self[position.asset].previous_close
            ) * position.quantity
            for position in self.portfolio.positions
        )

    @property
    def n_assets(self) -> int:
        return len(self.portfolio.positions)

    def __len__(self) -> int:
        return self.n_assets

    def __repr__(self) -> str:
        return (
            f"PortfolioSnapshot("
            f"{self.n_assets} assets, "
            f"value=${self.market_value:,.2f})"
        )
    
    