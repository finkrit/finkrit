# finkrit/packages/finq/portfolio/portfoliohistory.py

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class PortfolioHistory:
    """
    Historical portfolio market values.

    The value at each date represents the total market value of the
    portfolio using the current holdings.
    """

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
        return PortfolioHistory(
            dates=self.dates[item],
            value=self.value[item],
        )

    def __repr__(self):
        if self.empty:
            return "PortfolioHistory(empty)"

        return f"PortfolioHistory({self.start} -> {self.end}, {self.n_periods} observations)"
    
