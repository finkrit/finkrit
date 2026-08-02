# finkrit/packages/finkritq/data/providers/memoizing.py
"""
In-process memoization for history and snapshot fetches.

``MemoizingHistoryProvider`` wraps any HistoryProvider and caches results,
keyed by (ticker, start, resolved_end, interval). Solves the "5 questions,
5 downloads" problem within one process. Not persistent, gone on exit.

Freshness (F-2): an open-ended request (``end=None`` means "up to today") is
keyed by *today's date*, not by ``None``. So the cache serves the same daily
bars for the rest of the day but re-fetches once the date rolls over, and a
long-lived server process no longer serves day-one data indefinitely. This is
day-granular, which is the right resolution for daily bars. Intraday staleness
of *today's* bar is out of scope for v1 (a persistent, gap-filling store is v2).

``MemoizingSnapshotProvider`` is the spot-price counterpart with a short TTL
instead of a day key: a snapshot is "the price now", so it must expire in
minutes, not at midnight. The TTL exists so one dashboard interaction (a
prefetch warming the cache, then the view reading it) sees one consistent
quote per ticker without a second network round trip, while the next
interaction gets a fresh price.

A failed fetch raises rather than returning a value, so it is never cached, a
retry re-fetches. Hits and misses are logged at debug so an empty or slow fetch
can be traced without adding noise at the default level.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Callable

from loguru import logger

from finkritq.asset import Asset, AssetSnapshot
from finkritq.data.interfaces import HistoryProvider, SnapshotProvider
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
            logger.debug(f"history cache hit: {asset.ticker} {start} to {resolved_end} interval={interval}")
            return cached
        logger.debug(f"history cache miss: {asset.ticker} {start} to {resolved_end} interval={interval}")
        result = self._wrapped.history(asset, start=start, end=end, interval=interval)
        self._cache[key] = result
        return result

    def clear(self) -> None:
        self._cache.clear()


class MemoizingSnapshotProvider(SnapshotProvider):
    """
    Short-TTL cache over a SnapshotProvider.

    ``clock`` is injectable (monotonic seconds) so tests can advance time
    without sleeping. 60 seconds default: long enough to cover a prefetch
    followed by the view's own reads, short enough that a user refreshing for
    a new quote actually gets one.
    """

    def __init__(
            self,
            wrapped: SnapshotProvider,
            ttl_seconds: float = 60.0,
            clock: Callable[[], float] = time.monotonic,
        ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")
        self._wrapped = wrapped
        self._ttl = ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, AssetSnapshot]] = {}

    def snapshot(self, asset: Asset) -> AssetSnapshot:
        now = self._clock()
        hit = self._cache.get(asset.ticker)
        if hit is not None and now - hit[0] < self._ttl:
            logger.debug(f"snapshot cache hit: {asset.ticker}")
            return hit[1]
        logger.debug(f"snapshot cache miss: {asset.ticker}")
        snap = self._wrapped.snapshot(asset)
        self._cache[asset.ticker] = (now, snap)
        return snap

    def clear(self) -> None:
        self._cache.clear()
