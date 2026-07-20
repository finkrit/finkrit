# finkrit/packages/finkritq/tests/anal/performance/test_information_ratio.py
"""
Tests for the information ratio: annualized active return / tracking error.
Core checks use independent numpy oracles for both terms.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.information_ratio import (
    information_ratio,
    information_ratio_asset,
    information_ratio_from_prices,
    information_ratio_from_returns,
    portfolio_information_ratio,
)
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.tests.fixtures import MARKET_PRICES, make_price_history, make_stock

SIMPLE = ReturnCalculationMethod.SIMPLE

_R = np.array([0.02, -0.03, 0.01, -0.015, 0.025, -0.005, 0.012])
_B = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.0, 0.008])


def _geo_from_returns(returns, ppy):
    total = np.prod(1.0 + returns) - 1.0
    return (1.0 + total) ** (ppy / len(returns)) - 1.0


def _geo_from_prices(prices, ppy):
    return (prices[-1] / prices[0]) ** (ppy / (len(prices) - 1)) - 1.0


def _tracking_error(asset, benchmark, ppy):
    return np.std(asset - benchmark, ddof=1) * np.sqrt(ppy)


def _benchmark(length, seed):
    rng = np.random.default_rng(seed)
    return np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, length))), 4)


class TestInformationRatioFromReturns:

    def test_matches_independent_oracle(self):
        active = _geo_from_returns(_R, 12) - _geo_from_returns(_B, 12)
        expected = active / _tracking_error(_R, _B, 12)
        assert information_ratio_from_returns(_R, _B, method=SIMPLE, periods_per_year=12) == pytest.approx(expected)

    def test_matching_benchmark_is_nan(self):
        # Tracking the benchmark exactly means zero active risk (and zero active
        # return): 0 / 0 is undefined -> nan.
        assert np.isnan(information_ratio_from_returns(_R, _R))

    def test_positive_when_outperforming_with_varying_margin(self):
        # Beat the benchmark every period, but by a VARYING margin: the active
        # return is positive and its tracking error is nonzero, so the ratio is
        # positive. (A constant margin has zero tracking error and thus an
        # undefined, nan, information ratio -- active RISK is the variability of
        # the margin, not the margin itself.)
        benchmark = np.array([0.005, 0.004, 0.006, 0.005, 0.005])
        asset = benchmark + np.array([0.003, 0.001, 0.004, 0.002, 0.003])
        assert information_ratio_from_returns(asset, benchmark, method=SIMPLE, periods_per_year=12) > 0.0


class TestInformationRatioFromPrices:

    def test_matches_independent_oracle(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        active = _geo_from_prices(MARKET_PRICES, 252) - _geo_from_prices(bench, 252)
        te = _tracking_error(np.diff(np.log(MARKET_PRICES)), np.diff(np.log(bench)), 252)
        assert information_ratio_from_prices(MARKET_PRICES, bench) == pytest.approx(active / te)

    def test_history_wrapper_matches_prices(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        result = information_ratio(make_price_history(MARKET_PRICES), make_price_history(bench))
        assert result == pytest.approx(information_ratio_from_prices(MARKET_PRICES, bench))

    def test_asset_wrapper_uses_registry(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        registry = MagicMock()
        registry.history.side_effect = [make_price_history(MARKET_PRICES), make_price_history(bench)]
        result = information_ratio_asset(make_stock("A"), make_stock("BENCH"), registry)
        assert result == pytest.approx(information_ratio_from_prices(MARKET_PRICES, bench))


class TestPortfolioInformationRatio:

    def _bench(self):
        return make_price_history(_benchmark(60, 11))

    def test_matches_independent_oracle(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        active = _geo_from_prices(pd.value, 252) - _geo_from_prices(bench.close, 252)
        te = _tracking_error(np.diff(np.log(pd.value)), np.diff(np.log(bench.close)), 252)
        assert portfolio_information_ratio(pd, bench, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(active / te)

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_information_ratio(pd, bench, basis=basis))
