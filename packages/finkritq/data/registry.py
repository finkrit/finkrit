# finkrit/packages/finkritq/data/registry.py
"""
DataRegistry — the provider-agnostic entry point for market data.

Holds the registered history/snapshot providers and delegates to them. It
deals only in assets: turning a Portfolio into aligned market data is
PortfolioData's job (``PortfolioData.from_registry``), which calls back in
here per asset. Keeping the registry asset-only means the data layer no longer
imports the portfolio/domain layer, and ``history`` has an honest return type.
"""
from __future__ import annotations

from datetime import date

from finkritq.asset import Asset, AssetSnapshot
from finkritq.data.interfaces import HistoryProvider, SnapshotProvider
from finkritq.datatype import PriceHistory


class DataRegistry:

    def __init__(self) -> None:
        self._history_provider: HistoryProvider | None = None
        self._snapshot_provider: SnapshotProvider | None = None

    def register_history(self, provider: HistoryProvider) -> None:
        self._history_provider = provider

    def register_snapshot(self, provider: SnapshotProvider) -> None:
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

    def snapshot(self, asset: Asset) -> AssetSnapshot:
        if self._snapshot_provider is None:
            raise RuntimeError("Snapshot provider has not been registered.")

        return self._snapshot_provider.snapshot(asset)
