# finkrit/packages/finkritq/tests/anal/performance/test_calmar_ratio.py
"""
Tests for the Calmar ratio.

Core checks use an independent numpy oracle (raw drawdown math) plus one fully
hand-worked case with a known answer. The from-returns path must match the
from-prices path exactly, since drawdown is scale-invariant.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.annualized_return import portfolio_annualized_return
from finkritq.anal.performance.calmar_ratio import (
    calmar_ratio,
    calmar_ratio_asset,
    calmar_ratio_from_prices,
    calmar_ratio_from_returns,
    portfolio_calmar_ratio,
)
from finkritq.anal.risk.drawdown import portfolio_maximum_drawdown
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.tests.fixtures import MARKET_PRICES, RISING_PRICES, make_price_history, make_stock

SIMPLE = ReturnCalculationMethod.SIMPLE
LOG = ReturnCalculationMethod.LOG


def _oracle_max_drawdown(levels):
    running_peak = np.maximum.accumulate(levels)
    return ((levels - running_peak) / running_peak).min()


def _oracle_calmar_from_prices(prices, periods_per_year):
    n = len(prices) - 1
    annualized = (prices[-1] / prices[0]) ** (periods_per_year / n) - 1.0
    return annualized / abs(_oracle_max_drawdown(prices))


class TestCalmarFromPrices:

    def test_hand_worked_case(self):
        # 100 -> 120 -> 90 -> 110. Worst drop is 120 -> 90 = -25%.
        # Total return 10% over 3 intervals; with ppy=3 that is one year, so
        # annualized = 10%. Calmar = 0.10 / 0.25 = 0.4.
        prices = np.array([100.0, 120.0, 90.0, 110.0])
        assert calmar_ratio_from_prices(prices, periods_per_year=3) == pytest.approx(0.4)

    def test_matches_independent_oracle(self):
        assert calmar_ratio_from_prices(MARKET_PRICES) == pytest.approx(
            _oracle_calmar_from_prices(MARKET_PRICES, 252)
        )

    def test_monotonic_rise_has_no_drawdown_and_is_nan(self):
        # RISING_PRICES only ever goes up, so maximum drawdown is exactly zero.
        assert np.isnan(calmar_ratio_from_prices(RISING_PRICES))


class TestCalmarFromReturns:

    def test_matches_from_prices_simple(self):
        # Drawdown is scale-invariant, so reconstructing wealth from returns must
        # reproduce the price-based Calmar exactly.
        prices = MARKET_PRICES
        simple_returns = prices[1:] / prices[:-1] - 1.0
        assert calmar_ratio_from_returns(simple_returns, method=SIMPLE) == pytest.approx(
            calmar_ratio_from_prices(prices)
        )

    def test_matches_from_prices_log(self):
        prices = MARKET_PRICES
        log_returns = np.diff(np.log(prices))
        assert calmar_ratio_from_returns(log_returns, method=LOG) == pytest.approx(
            calmar_ratio_from_prices(prices)
        )

    def test_counts_first_period_drawdown(self):
        # A -20% first period then recovery. The worst drawdown is that opening
        # -20%, which is only captured if wealth starts at 1.0 (the bug in
        # maximum_drawdown_from_returns is that it omits this leading 1.0).
        returns = np.array([-0.20, 0.05, 0.05])
        # wealth path 1.0 -> 0.8 -> 0.84 -> 0.882, worst drawdown -20%.
        prices = np.array([1.0, 0.8, 0.84, 0.882])
        assert calmar_ratio_from_returns(returns, method=SIMPLE) == pytest.approx(
            calmar_ratio_from_prices(prices, periods_per_year=252)
        )


class TestCalmarWrappers:

    def test_history_wrapper_matches_prices(self):
        history = make_price_history(MARKET_PRICES)
        assert calmar_ratio(history) == pytest.approx(calmar_ratio_from_prices(MARKET_PRICES))

    def test_asset_wrapper_uses_registry_history(self):
        registry = MagicMock()
        registry.history.return_value = make_price_history(MARKET_PRICES)
        result = calmar_ratio_asset(make_stock("XYZ"), registry)
        assert result == pytest.approx(calmar_ratio_from_prices(MARKET_PRICES))
        assert registry.history.called


class TestPortfolioCalmar:

    def test_uses_one_basis_for_both_terms(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            ann = portfolio_annualized_return(pd, basis=basis, periods_per_year=252)
            mdd = portfolio_maximum_drawdown(pd, basis=basis)
            assert portfolio_calmar_ratio(pd, basis=basis) == pytest.approx(ann / abs(mdd))

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_calmar_ratio(pd) == pytest.approx(
            portfolio_calmar_ratio(pd, basis=WeightingBasis.BUY_AND_HOLD)
        )

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_calmar_ratio(pd, basis=basis))
