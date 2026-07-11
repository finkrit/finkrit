# finkrit/packages/finq/data/registry.py

from __future__ import annotations

from datetime import date

from packages.finq.asset import Asset
from packages.finq.data.interfaces import HistoryProvider, SnapshotProvider
from packages.finq.datatype import PriceHistory
from packages.finq.portfolio import Portfolio, PortfolioData

class DataRegistry:

    def __init__(self):
        self._history_provider: HistoryProvider | None = None
        self._snapshot_provider: SnapshotProvider | None = None

    def register_history(self, provider: HistoryProvider):
        self._history_provider = provider

    def register_snapshot(self, provider: SnapshotProvider):
        self._snapshot_provider = provider

    def history(
        self,
        target: Asset | Portfolio,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        if self._history_provider is None:
            raise RuntimeError("History provider has not been registered.")

        if isinstance(target, Asset):
            return self._history_provider.history(
                asset=target,
                start=start,
                end=end,
                interval=interval,
            )

        if isinstance(target, Portfolio):
            return PortfolioData.from_registry(
                portfolio=target,
                registry=self,
                start=start,
                end=end,
                interval=interval,
            )

        raise TypeError(
            f"Unsupported type '{type(obj).__name__}'. "
            "Expected Asset or Portfolio."
        )

    def snapshot(self, asset: Asset):
        if self._snapshot_provider is None:
            raise RuntimeError("Snapshot provider has not been registered.")

        return self._snapshot_provider.snapshot(asset)
    
    