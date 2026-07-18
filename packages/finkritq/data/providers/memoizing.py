# finkrit/packages/finkritq/data/providers/memoizing.py
"""
In-process memoization for history fetches.

Wraps any HistoryProvider and caches results, keyed by
(ticker, start, resolved_end, interval). Solves the "5 questions -> 5
downloads" problem within one process. NOT persistent -- gone on exit.

Freshness (F-2): an open-ended request (``end=None`` means "up to today") is
keyed by *today's date*, not by ``None``. So the cache serves the same daily
bars for the rest of the day but re-fetches once the date rolls over -- a
long-lived server process no longer serves day-one data indefinitely. This is
day-granular, which is the right resolution for daily bars; intraday staleness
of *today's* bar is out of scope for v1 (a persistent, gap-filling store is v2).
"""
from __future__ import annotations

from datetime import date

from finkritq.asset import Asset
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import PriceHistory


class MemoizingHistoryProvider(HistoryProvider):
    def __init__(self, wrapped: HistoryProvider) -> None:
        self._wrapped = wrapped
        self._cache: dict[tuple[str, date | None, date, str], PriceHistory] = {}

    def history(
        self,
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        # Resolve an open-ended request to today for the cache key, so the
        # entry expires naturally when the day changes (see module docstring).
        resolved_end = end if end is not None else date.today()
        key = (asset.ticker, start, resolved_end, interval)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._wrapped.history(asset, start=start, end=end, interval=interval)
        self._cache[key] = result
        return result

    def clear(self) -> None:
        self._cache.clear()
