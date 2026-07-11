# finkrit/packages/finq/portfolio/portfoliohistory.py

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray


from packages.finq.data.registry import DataRegistry
from packages.finq.portfolio.portfolio import Portfolio
from packages.finq.datatype import PriceHistory


@dataclass(frozen=True, slots=True)
class PortfolioHistory:
    """
    Historical portfolio market values.

    The value at each date represents the total market value of the
    portfolio using the current holdings.
    """

    portfolio: Portfolio
    dates: NDArray[np.datetime64]
    value: NDArray[np.float64]

    def __post_init__(self):

        if self.dates.ndim != 1:
            raise ValueError("dates must be one-dimensional.")

        if self.value.ndim != 1:
            raise ValueError("value must be one-dimensional.")

        if len(self.dates) != len(self.value):
            raise ValueError("dates and value must have the same length.")

        if len(self.dates) > 1:
            if np.any(self.dates[:-1] >= self.dates[1:]):
                raise ValueError("Dates must be strictly increasing.")

    @property
    def empty(self) -> bool:
        return len(self.dates) == 0

    @property
    def start(self):
        return None if self.empty else self.dates[0]

    @property
    def end(self):
        return None if self.empty else self.dates[-1]

    @property
    def n_periods(self) -> int:
        return len(self.dates)

    def __len__(self):
        return self.n_periods

    def __getitem__(self, item):
        return PortfolioHistory(portfolio=self.portfolio, dates=self.dates[item], value=self.value[item])

    def __repr__(self):
        if self.empty:
            return "PortfolioHistory(empty)"
        return f"PortfolioHistory({self.start} -> {self.end}, {self.n_periods} observations)"
    

    @classmethod
    def from_portfolio(
        cls,
        portfolio: Portfolio,
        registry: DataRegistry,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        max_workers: int | None = None,
    ) -> "PortfolioHistory":

        if len(portfolio.positions) == 0:
            raise ValueError("Portfolio contains no positions.")

        def _fetch(position):
            history = registry.history(
                asset=position.asset,
                start=start,
                end=end,
                interval=interval,
            )
            return position, history

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_fetch, portfolio.positions))

        positions = [r[0] for r in results]
        histories = [r[1] for r in results]

        # Align histories
        histories = PriceHistory.align_many(histories)
        if not histories or histories[0].empty:
            raise ValueError("Portfolio histories have no overlapping dates.")

        # Aggregate values
        values = np.zeros(len(histories[0]), dtype=np.float64)

        for position, history in zip(positions, histories):
            values += history.close * position.quantity

        return cls(portfolio=portfolio, dates=histories[0].dates, value=values)
    
    
