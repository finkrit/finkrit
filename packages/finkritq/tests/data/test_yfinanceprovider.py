# finkrit/packages/finkritq/tests/data/test_yfinanceprovider.py
"""
Tests for the yfinance to PriceHistory boundary.

The one that matters most here is NaN hygiene. yfinance routinely appends a row
for the most recent, not-yet-settled session with a NaN close, and a single NaN
close propagates as NaN through every covariance and volatility, which reaches
the caller as blank numbers with no reason attached. _to_price_history must drop
those rows at the boundary so the analytics only ever see finite prices.

These need pandas (the finkritq[data] extra), so they skip when it is absent.
"""
from __future__ import annotations

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("yfinance")

from finkritq.data.providers.yfinanceprovider import YFinanceProvider


def _frame(dates: list[str], closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    close = np.asarray(closes, dtype=np.float64)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Volume": np.ones(n, dtype=np.int64),
        },
        index=pd.to_datetime(dates),
    )


class TestToPriceHistoryNaNHygiene:

    def test_trailing_nan_close_is_dropped(self):
        # The classic case, a NaN close on the latest unsettled bar.
        df = _frame(
            ["2026-07-22", "2026-07-23", "2026-07-24"],
            [100.0, 101.0, float("nan")],
        )
        history = YFinanceProvider._to_price_history(df)
        assert len(history.close) == 2
        assert np.all(np.isfinite(history.close))
        assert str(history.dates[-1])[:10] == "2026-07-23"

    def test_mid_series_nan_close_is_dropped(self):
        df = _frame(
            ["2026-07-22", "2026-07-23", "2026-07-24"],
            [100.0, float("nan"), 102.0],
        )
        history = YFinanceProvider._to_price_history(df)
        assert len(history.close) == 2
        assert np.all(np.isfinite(history.close))

    def test_clean_frame_is_untouched(self):
        df = _frame(
            ["2026-07-22", "2026-07-23", "2026-07-24"],
            [100.0, 101.0, 102.0],
        )
        history = YFinanceProvider._to_price_history(df)
        assert len(history.close) == 3
        np.testing.assert_array_equal(history.close, [100.0, 101.0, 102.0])
