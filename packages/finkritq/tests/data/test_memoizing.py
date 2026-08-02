# finkritq/tests/data/test_memoizing.py
from __future__ import annotations

from datetime import date

import numpy as np

from finkritq.asset import AssetSnapshot, Stock
from finkritq.data.interfaces import HistoryProvider, SnapshotProvider
from finkritq.data.providers import MemoizingHistoryProvider, MemoizingSnapshotProvider
from finkritq.datatype import Currency, Exchange, PriceHistory


class _CountingProvider(HistoryProvider):
    def __init__(self):
        self.calls = 0

    def history(self, asset, start=None, end=None, interval="1d"):
        self.calls += 1
        dates = np.array([np.datetime64("2024-01-02")], dtype="datetime64[ns]")
        one = np.array([100.0])
        return PriceHistory(dates=dates, open=one, high=one, low=one, close=one,
                            volume=np.ones(1, dtype=np.int64))


def _stock(ticker="AAA"):
    return Stock(ticker=ticker, currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="x")


class TestMemoizingHistoryProvider:

    def test_second_identical_call_is_cached(self):
        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        memo.history(_stock(), start=date(2024, 1, 1), end=date(2024, 6, 1))
        memo.history(_stock(), start=date(2024, 1, 1), end=date(2024, 6, 1))
        assert inner.calls == 1

    def test_different_range_is_not_cached(self):
        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        memo.history(_stock(), start=date(2024, 1, 1), end=date(2024, 6, 1))
        memo.history(_stock(), start=date(2024, 1, 1), end=date(2024, 7, 1))
        assert inner.calls == 2

    def test_different_ticker_is_not_cached(self):
        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        memo.history(_stock("AAA"))
        memo.history(_stock("BBB"))
        assert inner.calls == 2

    def test_returns_same_object(self):
        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        first = memo.history(_stock())
        second = memo.history(_stock())
        assert first is second

    def test_clear_forces_refetch(self):
        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        memo.history(_stock())
        memo.clear()
        memo.history(_stock())
        assert inner.calls == 2

    def test_open_ended_end_is_keyed_by_today(self):
        # F-2: end=None ("up to today") and end=today() are the same request,
        # so they share a cache entry rather than the None key living forever.
        from datetime import date

        inner = _CountingProvider()
        memo = MemoizingHistoryProvider(inner)
        memo.history(_stock(), end=None)
        memo.history(_stock(), end=date.today())
        assert inner.calls == 1


class _CountingSnapshotProvider(SnapshotProvider):
    def __init__(self):
        self.calls = 0

    def snapshot(self, asset):
        self.calls += 1
        return AssetSnapshot(asset=asset, last_price=101.0, previous_close=100.0)


class TestMemoizingSnapshotProvider:
    """TTL cache over spot quotes. The clock is injected so the tests advance
    time explicitly instead of sleeping."""

    def _memo(self, ttl=60.0):
        inner = _CountingSnapshotProvider()
        now = [0.0]
        memo = MemoizingSnapshotProvider(inner, ttl_seconds=ttl, clock=lambda: now[0])
        return inner, memo, now

    def test_second_call_within_ttl_is_cached(self):
        inner, memo, _ = self._memo()
        memo.snapshot(_stock())
        memo.snapshot(_stock())
        assert inner.calls == 1

    def test_expired_entry_refetches(self):
        inner, memo, now = self._memo(ttl=60.0)
        memo.snapshot(_stock())
        now[0] = 61.0
        memo.snapshot(_stock())
        assert inner.calls == 2

    def test_different_ticker_is_not_cached(self):
        inner, memo, _ = self._memo()
        memo.snapshot(_stock("AAA"))
        memo.snapshot(_stock("BBB"))
        assert inner.calls == 2

    def test_clear_forces_refetch(self):
        inner, memo, _ = self._memo()
        memo.snapshot(_stock())
        memo.clear()
        memo.snapshot(_stock())
        assert inner.calls == 2

    def test_non_positive_ttl_refused(self):
        import pytest

        with pytest.raises(ValueError):
            MemoizingSnapshotProvider(_CountingSnapshotProvider(), ttl_seconds=0)
