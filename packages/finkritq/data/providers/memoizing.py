# finkrit/packages/finkritq/data/providers/memoizing.py
"""
Session-scoped in-memory memoization for history fetches.

v1 caching: wraps any HistoryProvider and caches results in-process, keyed
by (ticker, start, end, interval). Solves the "5 questions -> 5 downloads"
problem within one conversation/process. NOT persistent -- gone on exit.

Deliberately naive on staleness: within one short session, serving the same
daily bars across calls.
"""
from __future__ import annotations

from datetime import date

from finkritq.asset import Asset
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import PriceHistory


class MemoizingHistoryProvider(HistoryProvider):
    def __init__(self, wrapped: HistoryProvider) -> None:
        self._wrapped = wrapped
        self._cache: dict[tuple[str, date | None, date | None, str], PriceHistory] = {}

    def history(
        self,
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        key = (asset.ticker, start, end, interval)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._wrapped.history(asset, start=start, end=end, interval=interval)
        self._cache[key] = result
        return result

    def clear(self) -> None:
        self._cache.clear()
