# finkrit/packages/finkritq/tests/anal/performance/test_sharpe_ratio.py
"""
Tests for the Sharpe ratio.

The core checks use an INDEPENDENT numpy oracle (raw np.prod / np.std), not the
performance/risk functions the implementation itself calls, so a shared bug in
the building blocks cannot make a tautological test pass. Behavior checks pin the
formula's structure (rf hits the numerator, zero vol is undefined) and, for a
portfolio, that both terms use one basis.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.sharpe_ratio import (
    portfolio_sharpe_ratio,
    sharpe_ratio,
    sharpe_ratio_asset,
    sharpe_ratio_from_prices,
    sharpe_ratio_from_returns,
)
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.tests.fixtures import MARKET_PRICES, make_price_history, make_stock

LOG = ReturnCalculationMethod.LOG
SIMPLE = ReturnCalculationMethod.SIMPLE

# A small, fixed return series so the oracle can be reasoned about by hand.
_RETURNS = np.array([0.01, 0.02, -0.015, 0.005, 0.008, -0.004])


def _oracle_sharpe_from_simple_returns(returns, risk_free_rate, periods_per_year):
    """Sharpe computed from first principles, independent of the implementation."""
    n = len(returns)
    total = np.prod(1.0 + returns) - 1.0                       # simple compounding
    annualized = (1.0 + total) ** (periods_per_year / n) - 1.0  # geometric CAGR
    vol = np.std(returns, ddof=1) * np.sqrt(periods_per_year)   # annualized std
    return (annualized - risk_free_rate) / vol


class TestSharpeFromReturns:

    def test_matches_independent_oracle(self):
        expected = _oracle_sharpe_from_simple_returns(_RETURNS, 0.0, 12)
        actual = sharpe_ratio_from_returns(_RETURNS, method=SIMPLE, periods_per_year=12)
        assert actual == pytest.approx(expected)

    def test_risk_free_rate_matches_oracle(self):
        rf = 0.03
        expected = _oracle_sharpe_from_simple_returns(_RETURNS, rf, 12)
        actual = sharpe_ratio_from_returns(_RETURNS, method=SIMPLE, risk_free_rate=rf, periods_per_year=12)
        assert actual == pytest.approx(expected)

    def test_risk_free_rate_hits_numerator_not_denominator(self):
        # Raising rf must lower Sharpe by exactly rf / volatility, proving rf is
        # subtracted from the numerator. Wrong wiring (rf in the denominator)
        # would not give this linear drop.
        vol = np.std(_RETURNS, ddof=1) * np.sqrt(12)
        base = sharpe_ratio_from_returns(_RETURNS, method=SIMPLE, risk_free_rate=0.0, periods_per_year=12)
        charged = sharpe_ratio_from_returns(_RETURNS, method=SIMPLE, risk_free_rate=0.03, periods_per_year=12)
        assert base - charged == pytest.approx(0.03 / vol)

    def test_zero_volatility_is_nan(self):
        # Exactly-constant returns give exactly zero variance. (A non-zero
        # constant like 0.001 is not binary-representable, so np.var leaves a
        # ~1e-19 residue and volatility is not exactly zero -- np.zeros is.)
        flat = np.zeros(30)
        assert np.isnan(sharpe_ratio_from_returns(flat))


class TestSharpeFromPrices:

    def test_matches_independent_oracle(self):
        prices = MARKET_PRICES
        n = len(prices) - 1
        annualized = (prices[-1] / prices[0]) ** (252 / n) - 1.0
        log_returns = np.diff(np.log(prices))
        vol = np.std(log_returns, ddof=1) * np.sqrt(252)
        expected = annualized / vol
        assert sharpe_ratio_from_prices(MARKET_PRICES) == pytest.approx(expected)

    def test_history_wrapper_matches_prices(self):
        history = make_price_history(MARKET_PRICES)
        assert sharpe_ratio(history) == pytest.approx(sharpe_ratio_from_prices(MARKET_PRICES))

    def test_asset_wrapper_uses_registry_history(self):
        registry = MagicMock()
        registry.history.return_value = make_price_history(MARKET_PRICES)
        result = sharpe_ratio_asset(make_stock("XYZ"), registry)
        assert result == pytest.approx(sharpe_ratio_from_prices(MARKET_PRICES))
        assert registry.history.called


class TestPortfolioSharpe:

    def test_buy_and_hold_matches_independent_oracle(self, two_stock_portfolio_data):
        # Oracle straight off the value path: CAGR of the realized value over the
        # annualized std of its log returns.
        pd = two_stock_portfolio_data
        value = pd.value
        n = pd.n_periods - 1
        annualized = (value[-1] / value[0]) ** (252 / n) - 1.0
        vol = np.std(np.diff(np.log(value)), ddof=1) * np.sqrt(252)
        expected = annualized / vol
        assert portfolio_sharpe_ratio(pd, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(expected)

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_sharpe_ratio(pd) == pytest.approx(
            portfolio_sharpe_ratio(pd, basis=WeightingBasis.BUY_AND_HOLD)
        )

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_sharpe_ratio(pd, basis=basis))
