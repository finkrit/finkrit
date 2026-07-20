# finkrit/packages/finkritq/tests/anal/performance/test_total_return.py
"""
Tests for total (cumulative) return.

The load-bearing property: however the series is defined (log or simple), the
total return of a price path must equal the exact end/start price ratio minus 1.
"""
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from finkritq.anal.performance.total_return import (
    portfolio_total_return,
    total_return,
    total_return_asset,
    total_return_from_prices,
    total_return_from_returns,
)
from finkritq.datatype import ReturnCalculationMethod, WeightingBasis
from finkritq.transform.returns import periodic_returns
from finkritq.tests.fixtures import (
    FLAT_PRICES,
    MARKET_PRICES,
    RISING_PRICES,
    make_price_history,
    make_stock,
)


class TestTotalReturnFromReturns:

    def test_simple_returns_compound_multiplicatively(self):
        returns = np.array([0.10, -0.05, 0.02])
        expected = (1.10 * 0.95 * 1.02) - 1.0
        actual = total_return_from_returns(returns, method=ReturnCalculationMethod.SIMPLE)
        assert actual == pytest.approx(expected)

    def test_log_returns_add(self):
        returns = np.array([0.10, -0.05, 0.02])
        expected = np.expm1(returns.sum())
        actual = total_return_from_returns(returns, method=ReturnCalculationMethod.LOG)
        assert actual == pytest.approx(expected)

    def test_empty_series_is_zero(self):
        empty = np.array([], dtype=np.float64)
        assert total_return_from_returns(empty, method=ReturnCalculationMethod.LOG) == pytest.approx(0.0)
        assert total_return_from_returns(empty, method=ReturnCalculationMethod.SIMPLE) == pytest.approx(0.0)

    def test_zero_returns_give_zero_total(self):
        assert total_return_from_returns(np.zeros(20), method=ReturnCalculationMethod.SIMPLE) == pytest.approx(0.0)

    def test_unsupported_method_raises(self):
        with pytest.raises(ValueError):
            total_return_from_returns(np.zeros(5), method="nope")  # type: ignore[arg-type]


class TestTotalReturnFromPrices:

    def test_equals_exact_price_ratio(self):
        expected = MARKET_PRICES[-1] / MARKET_PRICES[0] - 1.0
        assert total_return_from_prices(MARKET_PRICES) == pytest.approx(expected)

    def test_matches_compounded_returns_either_convention(self):
        # The endpoint ratio must equal compounding the periodic returns, whether
        # those returns were built as log or simple.
        direct = total_return_from_prices(MARKET_PRICES)
        via_log = total_return_from_returns(
            periodic_returns(MARKET_PRICES, ReturnCalculationMethod.LOG),
            method=ReturnCalculationMethod.LOG,
        )
        via_simple = total_return_from_returns(
            periodic_returns(MARKET_PRICES, ReturnCalculationMethod.SIMPLE),
            method=ReturnCalculationMethod.SIMPLE,
        )
        assert direct == pytest.approx(via_log)
        assert direct == pytest.approx(via_simple)

    def test_flat_prices_zero(self):
        assert total_return_from_prices(FLAT_PRICES) == pytest.approx(0.0, abs=1e-12)

    def test_rising_prices_positive(self):
        expected = RISING_PRICES[-1] / RISING_PRICES[0] - 1.0
        assert total_return_from_prices(RISING_PRICES) == pytest.approx(expected)
        assert total_return_from_prices(RISING_PRICES) > 0.0


class TestTotalReturnWrappers:

    def test_history_wrapper_matches_prices(self):
        history = make_price_history(MARKET_PRICES)
        assert total_return(history) == pytest.approx(total_return_from_prices(MARKET_PRICES))

    def test_asset_wrapper_uses_registry_history(self):
        history = make_price_history(MARKET_PRICES)
        registry = MagicMock()
        registry.history.return_value = history
        result = total_return_asset(make_stock("XYZ"), registry)
        assert result == pytest.approx(total_return_from_prices(MARKET_PRICES))
        assert registry.history.called


class TestPortfolioTotalReturn:

    def test_buy_and_hold_equals_value_path_ratio(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        expected = pd.value[-1] / pd.value[0] - 1.0
        actual = portfolio_total_return(pd, basis=WeightingBasis.BUY_AND_HOLD)
        assert actual == pytest.approx(expected)

    def test_default_basis_is_buy_and_hold(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_total_return(pd) == pytest.approx(
            portfolio_total_return(pd, basis=WeightingBasis.BUY_AND_HOLD)
        )

    def test_both_bases_finite_and_distinct(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bh = portfolio_total_return(pd, basis=WeightingBasis.BUY_AND_HOLD)
        cm = portfolio_total_return(pd, basis=WeightingBasis.CONSTANT_MIX)
        assert np.isfinite(bh) and np.isfinite(cm)
        assert bh != pytest.approx(cm, rel=1e-9)

    def test_constant_mix_compounds_simple_weighted_returns(self, two_stock_portfolio_data):
        # A rebalanced portfolio's period return is the weighted sum of SIMPLE
        # asset returns; total return compounds those. Guard against a log-return
        # regression (exp(sum(w.log_r)) - 1 is NOT the constant-mix total return).
        pd = two_stock_portfolio_data
        simple_series = pd.constant_mix_returns(ReturnCalculationMethod.SIMPLE)
        expected = float(np.prod(1.0 + simple_series) - 1.0)
        assert portfolio_total_return(pd, basis=WeightingBasis.CONSTANT_MIX) == pytest.approx(expected)

