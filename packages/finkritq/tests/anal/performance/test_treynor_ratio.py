# finkrit/packages/finkritq/tests/anal/performance/test_treynor_ratio.py
"""
Tests for the Treynor ratio: (annualized return - rf) / beta.
Core checks use independent numpy oracles for the geometric return and beta.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.treynor_ratio import (
    portfolio_treynor_ratio,
    treynor_ratio,
    treynor_ratio_asset,
    treynor_ratio_from_prices,
    treynor_ratio_from_returns,
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


def _benchmark(length, seed):
    rng = np.random.default_rng(seed)
    return np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, length))), 4)


class TestTreynorFromReturns:

    def test_matches_independent_oracle(self):
        expected = _geo_from_returns(_R, 12) / _beta(_R, _B)
        assert treynor_ratio_from_returns(_R, _B, method=SIMPLE, periods_per_year=12) == pytest.approx(expected)

    def test_risk_free_rate_hits_numerator(self):
        beta = _beta(_R, _B)
        base = treynor_ratio_from_returns(_R, _B, method=SIMPLE, risk_free_rate=0.0, periods_per_year=12)
        charged = treynor_ratio_from_returns(_R, _B, method=SIMPLE, risk_free_rate=0.03, periods_per_year=12)
        assert base - charged == pytest.approx(0.03 / beta)

    def test_zero_variance_benchmark_is_nan(self):
        # A benchmark with no variance gives an undefined beta and thus Treynor.
        assert np.isnan(treynor_ratio_from_returns(_R, np.zeros(len(_R))))


class TestTreynorFromPrices:

    def test_matches_independent_oracle(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        ann = _geo_from_prices(MARKET_PRICES, 252)
        beta = _beta(np.diff(np.log(MARKET_PRICES)), np.diff(np.log(bench)))
        assert treynor_ratio_from_prices(MARKET_PRICES, bench) == pytest.approx(ann / beta)

    def test_history_wrapper_matches_prices(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        result = treynor_ratio(make_price_history(MARKET_PRICES), make_price_history(bench))
        assert result == pytest.approx(treynor_ratio_from_prices(MARKET_PRICES, bench))

    def test_asset_wrapper_uses_registry(self):
        bench = _benchmark(len(MARKET_PRICES), 3)
        registry = MagicMock()
        registry.history.side_effect = [make_price_history(MARKET_PRICES), make_price_history(bench)]
        result = treynor_ratio_asset(make_stock("A"), make_stock("BENCH"), registry)
        assert result == pytest.approx(treynor_ratio_from_prices(MARKET_PRICES, bench))


class TestPortfolioTreynor:

    def _bench(self):
        return make_price_history(_benchmark(60, 11))

    def test_matches_independent_oracle(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        ann = _geo_from_prices(pd.value, 252)
        # Portfolio + benchmark returns are simple at the portfolio level.
        beta = _beta(pd.value[1:] / pd.value[:-1] - 1.0, bench.close[1:] / bench.close[:-1] - 1.0)
        assert portfolio_treynor_ratio(pd, bench, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(ann / beta)

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = self._bench()
        assert portfolio_treynor_ratio(pd, bench) == pytest.approx(
            portfolio_treynor_ratio(pd, bench, basis=WeightingBasis.BUY_AND_HOLD)
        )
