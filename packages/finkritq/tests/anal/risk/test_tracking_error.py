# finkrit/packages/finkritq/tests/anal/risk/test_tracking_error.py
"""
Tests for tracking error (annualized std of active, benchmark-relative returns).
Core checks use an independent numpy oracle (raw np.std of the difference).
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.tracking_error import (
    portfolio_tracking_error,
    tracking_error,
    tracking_error_from_prices,
    tracking_error_from_returns,
)
from finkritq.datatype import WeightingBasis
from finkritq.tests.fixtures import MARKET_PRICES, make_price_history

_R = np.array([0.01, -0.02, 0.03, 0.00, 0.015, -0.008])
_B = np.array([0.005, -0.01, 0.02, 0.005, 0.01, -0.004])


def _benchmark_60():
    rng = np.random.default_rng(11)
    closes = np.round(200.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.011, 60))), 4)
    return make_price_history(closes)


class TestTrackingErrorFromReturns:

    def test_matches_independent_oracle(self):
        expected = np.std(_R - _B, ddof=1) * np.sqrt(252)
        assert tracking_error_from_returns(_R, _B) == pytest.approx(expected)

    def test_identical_series_is_zero(self):
        assert tracking_error_from_returns(_R, _R) == pytest.approx(0.0)

    def test_not_annualized(self):
        assert tracking_error_from_returns(_R, _B, annualized=False) == pytest.approx(
            np.std(_R - _B, ddof=1)
        )

    def test_annualization_scales_by_sqrt_periods(self):
        daily = tracking_error_from_returns(_R, _B, annualized=False)
        annual = tracking_error_from_returns(_R, _B, annualized=True)
        assert annual == pytest.approx(daily * np.sqrt(252))

    def test_single_observation_is_nan(self):
        assert np.isnan(tracking_error_from_returns(np.array([0.01]), np.array([0.005])))


class TestTrackingErrorFromPrices:

    def test_proportional_prices_have_zero_tracking_error(self):
        # A benchmark that is a constant multiple has identical returns, so the
        # active series is zero.
        assert tracking_error_from_prices(MARKET_PRICES, MARKET_PRICES * 3.0) == pytest.approx(0.0)

    def test_matches_independent_oracle(self):
        rng = np.random.default_rng(3)
        bench = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(MARKET_PRICES)))), 4)
        active = np.diff(np.log(MARKET_PRICES)) - np.diff(np.log(bench))
        expected = np.std(active, ddof=1) * np.sqrt(252)
        assert tracking_error_from_prices(MARKET_PRICES, bench) == pytest.approx(expected)

    def test_history_wrapper_matches_prices(self):
        rng = np.random.default_rng(3)
        bench = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(MARKET_PRICES)))), 4)
        assert tracking_error(
            make_price_history(MARKET_PRICES), make_price_history(bench)
        ) == pytest.approx(tracking_error_from_prices(MARKET_PRICES, bench))


class TestPortfolioTrackingError:

    def test_matches_independent_oracle(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = _benchmark_60()  # same 60 dates as the portfolio -> aligns exactly
        port_returns = np.diff(np.log(pd.value))            # BUY_AND_HOLD realized
        bench_returns = np.diff(np.log(bench.close))
        expected = np.std(port_returns - bench_returns, ddof=1) * np.sqrt(252)
        assert portfolio_tracking_error(pd, bench, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(expected)

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = _benchmark_60()
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_tracking_error(pd, bench, basis=basis))
