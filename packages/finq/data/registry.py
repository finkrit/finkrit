# finkrit/packages/finq/data/registry.py

from datetime import date
from packages.finq.asset import Asset
from packages.finq.data.interfaces import HistoryProvider, SnapshotProvider
from packages.finq.datatype import PriceHistory

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
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        if self._history_provider is None:
            raise RuntimeError("History provider has not been registered.")

        return self._history_provider.history(
            asset=asset,
            start=start,
            end=end,
            interval=interval,
        )

    def snapshot(self, asset: Asset):
        if self._snapshot_provider is None:
            raise RuntimeError("Snapshot provider has not been registered.")

        return self._snapshot_provider.snapshot(asset)
    
    