from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.returns import calculate_returns
from packages.finq.asset import Asset
from packages.finq.datatype import PriceHistory, ReturnCalculationMethod
from packages.finq.portfolio import Portfolio

if TYPE_CHECKING:
    from packages.finq.data.registry import DataRegistry


@dataclass(frozen=True, slots=True)
class PortfolioData:
    """
    Market data for a portfolio.

    Stores aligned price histories for each holding and exposes
    derived portfolio-level series and analytics.
    """

    portfolio: Portfolio
    _histories: dict[Asset, PriceHistory]

    @classmethod
    def from_registry(
        cls,
        portfolio: Portfolio,
        registry: DataRegistry,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        max_workers: int | None = None,
    ) -> "PortfolioData":

        if len(portfolio.positions) == 0:
            raise ValueError("Portfolio contains no positions.")

        def fetch(position):
            return (
                position.asset,
                registry.history(
                    target=position.asset,
                    start=start,
                    end=end,
                    interval=interval,
                ),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(fetch, portfolio.positions))

        assets = [asset for asset, _ in results]
        histories = [history for _, history in results]
        histories = PriceHistory.align_many(histories)
        return cls(portfolio=portfolio, _histories=dict(zip(assets, histories)))

    def __post_init__(self):

        if not self._histories:
            raise ValueError("PortfolioData requires at least one history.")

        missing = [p.asset for p in self.portfolio.positions if p.asset not in self._histories]
        if missing:
            raise ValueError("Missing histories for: , ".join(asset.ticker for asset in missing))

        first = next(iter(self._histories.values()))
        for asset, history in self._histories.items():

            if len(history) != len(first):
                raise ValueError(f"{asset.ticker} history has different length.")

            if not np.array_equal(history.dates, first.dates):
                raise ValueError(f"{asset.ticker} history is not aligned.")

    def __getitem__(self, asset: Asset) -> PriceHistory:
        return self._histories[asset]

    @property
    def assets(self) -> tuple[Asset, ...]:
        return tuple(self._histories)

    @property
    def dates(self) -> NDArray[np.datetime64]:
        return next(iter(self._histories.values())).dates

    @property
    def value(self) -> NDArray[np.float64]:

        values = np.zeros(len(self), dtype=np.float64)
        for position in self.portfolio.positions:
            values += (
                self[position.asset].close
                * position.quantity
            )

        return values
    
    @property
    def histories(self) -> tuple[PriceHistory, ...]:
        return tuple(self._histories.values())
    
    @property
    def n_assets(self) -> int:
        return len(self._histories)
    
    @property
    def price_matrix(self) -> NDArray[np.float64]:
        """
        Matrix of closing prices.

        Shape
        -----
        (n_assets, n_periods)
        """
        return np.asarray([
            history.close
            for history in self.histories
        ])
    
    @property
    def n_periods(self) -> int:
        return len(self)

    @property
    def weights(self) -> dict[Asset, float]:

        values = {
            position.asset: self.latest_prices[position.asset] * position.quantity
            for position in self.portfolio.positions
            }
        total = sum(values.values())
        return {
            asset: value / total
            for asset, value in values.items()
        }
    
    @property
    def weight_vector(self) -> NDArray[np.float64]:
        total = self.value[-1]

        return np.array([
            self.latest_prices[position.asset] * position.quantity / total
            for position in self.portfolio.positions
        ])
    
    @property
    def start(self) -> np.datetime64:
        return self.dates[0]

    @property
    def end(self) -> np.datetime64:
        return self.dates[-1]
    
    @property
    def latest_prices(self) -> dict[Asset, float]:
        return {
            asset: history.close[-1]
            for asset, history in self.items()
        }

    def __len__(self):
        return len(self.dates)

    def __repr__(self):
        return (f"PortfolioData({len(self.assets)} assets, {self.start} -> {self.end}, {len(self)} observations)")
    
    def return_matrix(
        self,
        method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    ) -> NDArray[np.float64]:

        return np.vstack([
            calculate_returns(history.close, method)
            for history in self.histories
        ])
    
    def portfolio_returns(self, method: ReturnCalculationMethod = ReturnCalculationMethod.LOG) -> NDArray[np.float64]:
        return calculate_returns(self.value, method=method)
    

    def items(self) -> tuple[tuple[Asset, PriceHistory], ...]:
        return tuple(self._histories.items())

    def asset_returns(
        self,
        asset: Asset,
        method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    ) -> NDArray[np.float64]:

        return calculate_returns(self[asset].close, method=method)
    

