# finkrit/tests/risk/test_volatility.py
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from finkritq.anal.returns import calculate_returns
from finkritq.anal.risk.variance import variance_from_returns, portfolio_variance
from finkritq.anal.risk.volatility import (
    volatility_from_returns,
    volatility_from_prices,
    volatility,
    volatility_asset,
    portfolio_volatility,
)
from finkritq.tests.fixtures import make_price_history, make_stock
from finkritq.tests.fixtures import RETURNS_A, FLAT_PRICES, PRICES


class TestVolatilityFromReturns:

    def test_equals_sqrt_variance(self):
        var = variance_from_returns(RETURNS_A, annualized=False)
        vol = volatility_from_returns(RETURNS_A, annualized=False)
        assert vol == pytest.approx(np.sqrt(var), abs=1e-10)

    def test_annualized_positive(self):
        assert volatility_from_returns(RETURNS_A, annualized=True) > 0.0

    def test_zero_for_flat_returns(self):
        assert volatility_from_returns(np.zeros(20), annualized=False) == pytest.approx(0.0, abs=1e-12)

    def test_matches_numpy_std(self):
        expected = np.std(RETURNS_A, ddof=1)
        actual = volatility_from_returns(RETURNS_A, annualized=False)
        assert actual == pytest.approx(expected)

    def test_constant_returns_have_zero_volatility(self):
        returns = np.full(30, 0.015)
        assert volatility_from_returns(returns, annualized=False) == pytest.approx(0.0)

    def test_scaling_returns_scales_volatility(self):
        base = volatility_from_returns(RETURNS_A, annualized=False)
        scaled = volatility_from_returns(RETURNS_A * 2, annualized=False)
        assert scaled == pytest.approx(base * 2)

    def test_shifting_returns_does_not_change_volatility(self):
        base = volatility_from_returns(RETURNS_A, annualized=False)
        shifted = volatility_from_returns(RETURNS_A + 0.05, annualized=False)
        assert shifted == pytest.approx(base)

    def test_order_does_not_change_volatility(self):
        expected = volatility_from_returns(RETURNS_A, annualized=False)
        actual = volatility_from_returns(RETURNS_A[::-1], annualized=False)
        assert actual == pytest.approx(expected)

    def test_custom_periods_per_year(self):
        daily = volatility_from_returns(RETURNS_A, annualized=False)
        annual = volatility_from_returns(RETURNS_A, annualized=True, periods_per_year=365)
        assert annual == pytest.approx(daily * np.sqrt(365))

class TestVolatilityFromPrices:

    def test_non_negative_prices(self):
        assert volatility_from_prices(PRICES) >= 0.0

    def test_consistent_with_returns_version(self):
        returns = calculate_returns(PRICES)
        vp = volatility_from_prices(PRICES,   annualized=False)
        vr = volatility_from_returns(returns, annualized=False)
        assert vp == pytest.approx(vr, rel=1e-9)

    def test_flat_prices_have_zero_volatility(self):
        assert volatility_from_prices(FLAT_PRICES, annualized=False) == pytest.approx(0.0)

    def test_matches_numpy_std_prices(self):
        returns = calculate_returns(PRICES)
        expected = np.std(returns, ddof=1)
        actual = volatility_from_prices(PRICES, annualized=False)
        assert actual == pytest.approx(expected)

    def test_matches_returns_version(self):
        returns = calculate_returns(PRICES)
        expected = volatility_from_returns(returns, annualized=False)
        actual = volatility_from_prices(PRICES, annualized=False)

        assert actual == pytest.approx(expected)


class TestVolatilityHistory:

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        assert isinstance(volatility(h), float)

    def test_matches_price_version(self):
        history = make_price_history(PRICES)
        assert volatility(history, annualized=False) == pytest.approx(volatility_from_prices(PRICES, annualized=False))


class TestPortfolioVolatility:

    def test_positive(self, two_stock_portfolio_data):
        assert portfolio_volatility(two_stock_portfolio_data) > 0.0

    def test_equals_sqrt_portfolio_variance(self, two_stock_portfolio_data):
        pvar = portfolio_variance(two_stock_portfolio_data)
        pvol = portfolio_volatility(two_stock_portfolio_data)
        assert pvol == pytest.approx(np.sqrt(pvar), rel=1e-9)

    @patch("finkritq.anal.risk.volatility.portfolio_variance")
    def test_square_root_of_variance(self, mock_variance, two_stock_portfolio_data):
        mock_variance.return_value = 0.09
        assert portfolio_volatility(two_stock_portfolio_data) == pytest.approx(0.3)

    @patch("finkritq.anal.risk.volatility.portfolio_variance")
    def test_zero_variance_gives_zero_volatility(self, mock_variance, two_stock_portfolio_data):
        mock_variance.return_value = 0.0
        assert portfolio_volatility(two_stock_portfolio_data) == pytest.approx(0.0)


class TestVolatilityAsset:

    def _make_registry(self, history):
        registry = MagicMock()
        registry.history.return_value = history
        return registry

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        assert isinstance(volatility_asset(make_stock(), self._make_registry(h)), float)

    def test_non_negative(self):
        h = make_price_history(PRICES.tolist())
        assert volatility_asset(make_stock(), self._make_registry(h)) >= 0.0

    def test_matches_history_version(self):
        h = make_price_history(PRICES.tolist())
        assert volatility_asset(make_stock(), self._make_registry(h), annualized=False) == pytest.approx(volatility(h, annualized=False), rel=1e-9)

    def test_calls_registry_history(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        volatility_asset(make_stock(), registry)
        assert registry.history.called
