# finkrit/packages/finkritq/tests/anal/performance/test_jensens_alpha.py
"""
Tests for Jensen's alpha: return above the CAPM expectation for the beta taken.
Core checks use independent numpy oracles for the geometric returns and beta.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.jensens_alpha import (
    jensens_alpha,
    jensens_alpha_asset,
    jensens_alpha_from_prices,
    jensens_alpha_from_returns,
    portfolio_jensens_alpha,
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


def _beta(asset, benchmark):
    cov = np.cov(asset, benchmark, ddof=1)
    return cov[0, 1] / cov[1, 1]


def _oracle_alpha(asset_returns, benchmark_returns, rf, ppy):
    ann = _geo_from_returns(asset_returns, ppy)
    ann_b = _geo_from_returns(benchmark_returns, ppy)
    beta = _beta(asset_returns, benchmark_returns)
    return ann - (rf + beta * (ann_b - rf))


def _benchmark(length, seed):
    rng = np.random.default_rng(seed)
    return np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, length))), 4)


class TestJensensAlphaFromReturns:

    def test_matches_independent_oracle(self):
        expected = _oracle_alpha(_R, _B, 0.0, 12)
        assert jensens_alpha_from_returns(_R, _B, method=SIMPLE, periods_per_year=12) == pytest.approx(expected)

    def test_with_risk_free_rate(self):
        expected = _oracle_alpha(_R, _B, 0.04, 12)
        assert jensens_alpha_from_returns(_R, _B, method=SIMPLE, risk_free_rate=0.04, periods_per_year=12) == pytest.approx(expected)

    def test_self_benchmark_has_zero_alpha(self):
        # Against itself beta is 1 and the returns match, so CAPM expects exactly
        # the realized return: alpha is zero, for any risk-free rate.
        assert jensens_alpha_from_returns(_R, _R, method=SIMPLE, risk_free_rate=0.03, periods_per_year=12) == pytest.approx(0.0, abs=1e-12)


class TestJensensAlphaFromPrices:

    def test_matches_independent_oracle(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        ann = _geo_from_prices(MARKET_PRICES, 252)
        ann_b = _geo_from_prices(bench, 252)
        beta = _beta(np.diff(np.log(MARKET_PRICES)), np.diff(np.log(bench)))
        expected = ann - beta * ann_b  # rf = 0
        assert jensens_alpha_from_prices(MARKET_PRICES, bench) == pytest.approx(expected)

    def test_history_wrapper_matches_prices(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        result = jensens_alpha(make_price_history(MARKET_PRICES), make_price_history(bench))
        assert result == pytest.approx(jensens_alpha_from_prices(MARKET_PRICES, bench))

    def test_asset_wrapper_uses_registry(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        registry = MagicMock()
        registry.history.side_effect = [make_price_history(MARKET_PRICES), make_price_history(bench)]
        result = jensens_alpha_asset(make_stock("A"), make_stock("BENCH"), registry)
        assert result == pytest.approx(jensens_alpha_from_prices(MARKET_PRICES, bench))


class TestPortfolioJensensAlpha:

    def _bench(self):
        return make_price_history(_benchmark(60, 11))

    def test_matches_independent_oracle(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        ann = _geo_from_prices(pd.value, 252)
        ann_b = _geo_from_prices(bench.close, 252)
        beta = _beta(np.diff(np.log(pd.value)), np.diff(np.log(bench.close)))
        expected = ann - beta * ann_b  # rf = 0
        assert portfolio_jensens_alpha(pd, bench, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(expected)

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_jensens_alpha(pd, bench, basis=basis))
