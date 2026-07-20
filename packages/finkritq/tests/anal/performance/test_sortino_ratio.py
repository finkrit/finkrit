# finkrit/packages/finkritq/tests/anal/performance/test_sortino_ratio.py
"""
Tests for the Sortino ratio.

Core checks use an independent numpy oracle (raw downside-deviation math), so a
shared bug in the building blocks cannot make a tautological test pass. Behavior
checks pin the structure: rf hits the numerator, the target moves the downside
denominator, and only below-target dispersion is penalized.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.annualized_return import portfolio_annualized_return
from finkritq.anal.performance.sortino_ratio import (
    portfolio_sortino_ratio,
    sortino_ratio,
    sortino_ratio_asset,
    sortino_ratio_from_prices,
    sortino_ratio_from_returns,
)
from finkritq.anal.risk.downside_deviation import portfolio_downside_deviation
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.tests.fixtures import MARKET_PRICES, make_price_history, make_stock

SIMPLE = ReturnCalculationMethod.SIMPLE
LOG = ReturnCalculationMethod.LOG

# Mixed up/down series so there is genuine downside dispersion.
_RETURNS = np.array([0.02, -0.03, 0.01, -0.015, 0.025, -0.005, 0.012])


def _oracle_downside_deviation(returns, target, periods_per_year):
    downside = np.minimum(returns - target, 0.0)
    semivariance = np.mean(np.square(downside)) * periods_per_year
    return np.sqrt(semivariance)


def _oracle_sortino(returns, risk_free_rate, target, periods_per_year):
    n = len(returns)
    total = np.prod(1.0 + returns) - 1.0
    annualized = (1.0 + total) ** (periods_per_year / n) - 1.0
    downside = _oracle_downside_deviation(returns, target, periods_per_year)
    return (annualized - risk_free_rate) / downside


class TestSortinoFromReturns:

    def test_matches_independent_oracle(self):
        expected = _oracle_sortino(_RETURNS, 0.0, 0.0, 12)
        actual = sortino_ratio_from_returns(_RETURNS, method=SIMPLE, periods_per_year=12)
        assert actual == pytest.approx(expected)

    def test_risk_free_rate_hits_numerator(self):
        downside = _oracle_downside_deviation(_RETURNS, 0.0, 12)
        base = sortino_ratio_from_returns(_RETURNS, method=SIMPLE, risk_free_rate=0.0, periods_per_year=12)
        charged = sortino_ratio_from_returns(_RETURNS, method=SIMPLE, risk_free_rate=0.03, periods_per_year=12)
        assert base - charged == pytest.approx(0.03 / downside)

    def test_higher_target_raises_downside_and_lowers_ratio(self):
        # A higher MAR turns more (and larger) periods into downside, growing the
        # denominator, so the ratio must fall for a positive-numerator series.
        low = sortino_ratio_from_returns(_RETURNS, method=SIMPLE, target=0.0, periods_per_year=12)
        high = sortino_ratio_from_returns(_RETURNS, method=SIMPLE, target=0.02, periods_per_year=12)
        assert high < low

    def test_no_downside_is_nan(self):
        # Every return at or above the target -> zero downside deviation.
        up_only = np.array([0.01, 0.02, 0.0, 0.03])
        assert np.isnan(sortino_ratio_from_returns(up_only, method=SIMPLE, target=0.0))


class TestSortinoFromPrices:

    def test_matches_independent_oracle(self):
        prices = MARKET_PRICES
        n = len(prices) - 1
        annualized = (prices[-1] / prices[0]) ** (252 / n) - 1.0
        log_returns = np.diff(np.log(prices))
        downside = _oracle_downside_deviation(log_returns, 0.0, 252)
        expected = annualized / downside
        assert sortino_ratio_from_prices(MARKET_PRICES) == pytest.approx(expected)

    def test_history_wrapper_matches_prices(self):
        history = make_price_history(MARKET_PRICES)
        assert sortino_ratio(history) == pytest.approx(sortino_ratio_from_prices(MARKET_PRICES))

    def test_asset_wrapper_uses_registry_history(self):
        registry = MagicMock()
        registry.history.return_value = make_price_history(MARKET_PRICES)
        result = sortino_ratio_asset(make_stock("XYZ"), registry)
        assert result == pytest.approx(sortino_ratio_from_prices(MARKET_PRICES))
        assert registry.history.called


class TestPortfolioSortino:

    def test_uses_one_basis_for_both_terms(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            ann = portfolio_annualized_return(pd, basis=basis, periods_per_year=252)
            dd = portfolio_downside_deviation(pd, basis=basis, annualized=True, periods_per_year=252)
            assert portfolio_sortino_ratio(pd, basis=basis) == pytest.approx(ann / dd)

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_sortino_ratio(pd) == pytest.approx(
            portfolio_sortino_ratio(pd, basis=WeightingBasis.BUY_AND_HOLD)
        )

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_sortino_ratio(pd, basis=basis))
