# finkrit/packages/finq/datatype/pricehistory.py
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

@dataclass(frozen=True, slots=True)
class PriceHistory:
    """
    Historical OHLCV price data.

    All arrays must have the same length and correspond to the
    same sequence of observation dates.
    """

    dates: NDArray[np.datetime64]
    open: NDArray[np.float64]
    high: NDArray[np.float64]
    low: NDArray[np.float64]
    close: NDArray[np.float64]
    volume: NDArray[np.integer]

    def __post_init__(self):
        """Verify all have same length"""
        n = len(self.dates)
        arrays = {"open": self.open,
                  "high": self.high,
                  "low": self.low,
                  "close": self.close,
                  "volume": self.volume}

        # Check dimensions
        if self.dates.ndim != 1:
            raise ValueError("dates must be one-dimensional.")

        for name, array in arrays.items():
            if array.ndim != 1:
                raise ValueError(f"{name} must be one-dimensional.")
            if len(array) != n:
                raise ValueError(f"{name} has length {len(array)}, expected {n}.")
            
        # Check dates sorted
        if n > 1:
            if np.any(self.dates[:-1] >= self.dates[1:]):
                raise ValueError("Dates must be strictly increasing.")

    @property
    def start(self):
        return None if self.empty else self.dates[0]

    @property
    def end(self):
        return None if self.empty else self.dates[-1]

    @property
    def empty(self) -> bool:
        return len(self.dates) == 0

    @property
    def n_periods(self) -> int:
        return len(self.dates)

    def __len__(self):
        return self.n_periods

    def __getitem__(self, item):
        """
        Slice the price history.

        Examples
        --------
        history[-252:]
        history[100:200]
        """
        return PriceHistory(
            dates=self.dates[item],
            open=self.open[item],
            high=self.high[item],
            low=self.low[item],
            close=self.close[item],
            volume=self.volume[item],
        )

    def __repr__(self):
        if self.empty:
            return "PriceHistory(empty)"
        return f"PriceHistory({self.start} -> {self.end}, {self.n_periods} observations)"
    
    def align(self, other: "PriceHistory") -> tuple["PriceHistory", "PriceHistory"]:
        """
        Align two price histories on their common observation dates.

        Returns
        -------
        tuple[PriceHistory, PriceHistory]
            Two new PriceHistory objects containing only the dates
            present in both histories.

        TODO: also check if the dates are contiguous. if there are missing dates (most providers should be fine without this check)
        """

        common_dates = np.intersect1d(self.dates, other.dates)

        self_idx = np.isin(self.dates, common_dates)
        other_idx = np.isin(other.dates, common_dates)

        return (
            PriceHistory(
                dates=self.dates[self_idx],
                open=self.open[self_idx],
                high=self.high[self_idx],
                low=self.low[self_idx],
                close=self.close[self_idx],
                volume=self.volume[self_idx],
            ),
            PriceHistory(
                dates=other.dates[other_idx],
                open=other.open[other_idx],
                high=other.high[other_idx],
                low=other.low[other_idx],
                close=other.close[other_idx],
                volume=other.volume[other_idx],
            ),
        )
        
