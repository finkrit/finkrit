# finkrit/packages/finkritq/tests/anal/performance/test_annualized_return.py
"""
Tests for annualized (geometric / CAGR) return.

Load-bearing properties:
  1. over exactly one year the annualized return equals the total return, and
  2. the period count is compounding intervals, not observations.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.annualized_return import (
    annualized_return,
    annualized_return_asset,
    annualized_return_from_prices,
    annualized_return_from_returns,
    portfolio_annualized_return,
)
from finkritq.anal.performance.total_return import (
    portfolio_total_return,
    total_return_from_prices,
    total_return_from_returns,
)
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.tests.fixtures import (
    FLAT_PRICES,
    MARKET_PRICES,
    RISING_PRICES,
    make_price_history,
    make_stock,
)

LOG = ReturnCalculationMethod.LOG
SIMPLE = ReturnCalculationMethod.SIMPLE


def _cagr(total: float, n_periods: int, periods_per_year: int) -> float:
    years = n_periods / periods_per_year
    return (1.0 + total) ** (1.0 / years) - 1.0


class TestAnnualizedReturnFromReturns:

    def test_one_year_window_equals_total_return(self):
        # 12 monthly periods with periods_per_year=12 span exactly one year, so
        # annualizing must be a no-op: CAGR == total return.
        r = np.full(12, 0.01)
        total = total_return_from_returns(r, method=SIMPLE)
        assert annualized_return_from_returns(r, method=SIMPLE, periods_per_year=12) == pytest.approx(total)

    def test_two_year_window_takes_geometric_root(self):
        r = np.full(24, 0.01)
        total = total_return_from_returns(r, method=SIMPLE)
        expected = (1.0 + total) ** 0.5 - 1.0  # two years -> square root
        assert annualized_return_from_returns(r, method=SIMPLE, periods_per_year=12) == pytest.approx(expected)

    def test_matches_manual_cagr(self):
        expected = _cagr(total_return_from_returns(_LOG_RETURNS, method=LOG), len(_LOG_RETURNS), 252)
        assert annualized_return_from_returns(_LOG_RETURNS, method=LOG, periods_per_year=252) == pytest.approx(expected)

    def test_empty_series_is_zero(self):
        assert annualized_return_from_returns(np.array([]), method=LOG) == pytest.approx(0.0)

    def test_total_loss_annualizes_to_minus_one(self):
        # A -100% simple return drops wealth to zero; annualized is -100%.
        r = np.array([-1.0])
        assert annualized_return_from_returns(r, method=SIMPLE, periods_per_year=1) == pytest.approx(-1.0)


class TestAnnualizedReturnFromPrices:

    def test_uses_intervals_not_observations(self):
        # 2 prices -> 1 interval. periods_per_year=1 -> one-year window -> CAGR
        # equals the simple total return.
        prices = np.array([100.0, 121.0])
        assert annualized_return_from_prices(prices, periods_per_year=1) == pytest.approx(0.21)

    def test_sub_year_window_extrapolates(self):
        # 1 interval, periods_per_year=2 -> half a year -> squared.
        prices = np.array([100.0, 121.0])
        assert annualized_return_from_prices(prices, periods_per_year=2) == pytest.approx(1.21 ** 2 - 1.0)

    def test_matches_manual_cagr(self):
        expected = _cagr(total_return_from_prices(MARKET_PRICES), len(MARKET_PRICES) - 1, 252)
        assert annualized_return_from_prices(MARKET_PRICES, periods_per_year=252) == pytest.approx(expected)

    def test_flat_prices_zero(self):
        assert annualized_return_from_prices(FLAT_PRICES) == pytest.approx(0.0, abs=1e-12)

    def test_rising_prices_positive(self):
        assert annualized_return_from_prices(RISING_PRICES) > 0.0

    def test_single_price_is_zero(self):
        assert annualized_return_from_prices(np.array([100.0])) == pytest.approx(0.0)


class TestAnnualizedReturnWrappers:

    def test_history_wrapper_matches_prices(self):
        history = make_price_history(MARKET_PRICES)
        assert annualized_return(history) == pytest.approx(annualized_return_from_prices(MARKET_PRICES))

    def test_asset_wrapper_uses_registry_history(self):
        registry = MagicMock()
        registry.history.return_value = make_price_history(MARKET_PRICES)
        result = annualized_return_asset(make_stock("XYZ"), registry)
        assert result == pytest.approx(annualized_return_from_prices(MARKET_PRICES))
        assert registry.history.called


class TestPortfolioAnnualizedReturn:

    def test_annualizes_the_total_return(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        total = portfolio_total_return(pd, basis=WeightingBasis.BUY_AND_HOLD)
        expected = _cagr(total, pd.n_periods - 1, 252)
        assert portfolio_annualized_return(pd, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(expected)

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_annualized_return(pd) == pytest.approx(
            portfolio_annualized_return(pd, basis=WeightingBasis.BUY_AND_HOLD)
        )

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_annualized_return(pd, basis=basis))


# 60 deterministic daily log returns (independent of the price fixtures' exact shape).
_LOG_RETURNS = np.diff(np.log(MARKET_PRICES))
