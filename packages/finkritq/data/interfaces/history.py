# finkrit/packages/finkritq/data/interfaces/history.py
from abc import ABC, abstractmethod
from datetime import date
from packages.finkritq.datatype import PriceHistory

from packages.finkritq.asset import Asset


class HistoryProvider(ABC):
    """Abstract interface for retrieving historical market data."""

    @abstractmethod
    def history(
        self,
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        """
        Retrieve historical price data for an asset.

        Parameters
        ----------
        asset : Asset
            The asset whose price history is requested.
        start : date | None
            Start date (inclusive).
        end : date | None
            End date (inclusive).
        interval : str
            Data frequency (e.g. "1d", "1wk", "1mo").

        Returns
        -------
        PriceHistory
            Historical OHLCV price data.
        """
        ...