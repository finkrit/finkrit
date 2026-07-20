# finkrit/tests/risk/test_semivariance.py
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from finkritq.anal.risk.semivariance import (
    semivariance_from_returns,
    semivariance_from_prices,
    semivariance,
    semivariance_asset,
    portfolio_semivariance,
)
from finkritq.anal.risk.variance import variance_from_returns
from finkritq.transform.returns import periodic_returns
from finkritq.tests.fixtures import make_price_history, make_stock
from finkritq.tests.fixtures import RETURNS_A, PRICES, FLAT_PRICES


class TestSemivarianceFromReturns:

    def test_non_negative_returns(self):
        assert semivariance_from_returns(RETURNS_A, annualized=False) >= 0.0

    def test_le_full_variance(self):
        sv  = semivariance_from_returns(RETURNS_A, annualized=False)
        var = variance_from_returns(RETURNS_A,    annualized=False)
        assert sv <= var + 1e-10

    def test_zero_for_all_positive_returns(self):
        positive = np.array([0.01, 0.02, 0.03, 0.005], dtype=np.float64)
        assert semivariance_from_returns(positive, annualized=False) == pytest.approx(0.0, abs=1e-12)

    def test_annualized_equals_daily_times_252(self):
        daily  = semivariance_from_returns(RETURNS_A, annualized=False)
        annual = semivariance_from_returns(RETURNS_A, annualized=True)
        assert annual == pytest.approx(daily * 252, rel=1e-9)

    def test_matches_manual_calculation(self):
        downside = np.minimum(RETURNS_A, 0.0)
        expected = np.mean(np.square(downside))
        actual = semivariance_from_returns(RETURNS_A, annualized=False)

        assert actual == pytest.approx(expected)

    def test_constant_positive_returns_have_zero_semivariance(self):
        returns = np.full(30, 0.02)
        assert semivariance_from_returns(returns, annualized=False) == pytest.approx(0.0)

    def test_constant_negative_returns(self):
        returns = np.full(20, -0.01)
        expected = 0.0001

        assert semivariance_from_returns(returns, annualized=False) == pytest.approx(expected)

    def test_target_changes_semivariance(self):
        base = semivariance_from_returns(RETURNS_A, target=0.0, annualized=False)
        higher = semivariance_from_returns(RETURNS_A, target=0.01, annualized=False)

        assert higher >= base

    def test_custom_periods_per_year(self):
        daily = semivariance_from_returns(RETURNS_A, annualized=False)
        annual = semivariance_from_returns(RETURNS_A, annualized=True, periods_per_year=365)

        assert annual == pytest.approx(daily * 365)


class TestSemivarianceFromPrices:

    def test_non_negative_prices(self):
        assert semivariance_from_prices(PRICES) >= 0.0

    def test_flat_prices_have_zero_semivariance(self):
        assert semivariance_from_prices(FLAT_PRICES, annualized=False) == pytest.approx(0.0)

    def test_matches_returns_version(self):
        returns = periodic_returns(PRICES)

        expected = semivariance_from_returns(returns, annualized=False)
        actual = semivariance_from_prices(PRICES, annualized=False)

        assert actual == pytest.approx(expected)


class TestSemivarianceHistory:

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        assert isinstance(semivariance(h), float)

    def test_matches_price_version(self):
        history = make_price_history(PRICES)
        assert semivariance(history, annualized=False) == pytest.approx(semivariance_from_prices(PRICES, annualized=False))


class TestPortfolioSemivariance:

    def test_non_negative_portfolio(self, two_stock_portfolio_data):
        assert portfolio_semivariance(two_stock_portfolio_data) >= 0.0

    def test_le_portfolio_variance(self, two_stock_portfolio_data):
        from finkritq.anal.risk.variance import portfolio_variance
        sv  = portfolio_semivariance(two_stock_portfolio_data)
        var = portfolio_variance(two_stock_portfolio_data)
        assert sv <= var + 1e-10

    @patch("finkritq.anal.risk.semivariance.semivariance_from_returns")
    def test_delegates_to_semivariance_from_returns(self, mock_semivariance, two_stock_portfolio_data):
        mock_semivariance.return_value = 0.123
        result = portfolio_semivariance(two_stock_portfolio_data)
        assert result == pytest.approx(0.123)
        mock_semivariance.assert_called_once()


class TestSemivarianceAsset:

    def _make_registry(self, history):
        registry = MagicMock()
        registry.history.return_value = history
        return registry

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        assert isinstance(semivariance_asset(make_stock(), self._make_registry(h)), float)

    def test_non_negative(self):
        h = make_price_history(PRICES.tolist())
        assert semivariance_asset(make_stock(), self._make_registry(h)) >= 0.0

    def test_matches_history_version(self):
        h = make_price_history(PRICES.tolist())
        assert semivariance_asset(make_stock(), self._make_registry(h), annualized=False) == pytest.approx(semivariance(h, annualized=False), rel=1e-9)

    def test_calls_registry_history(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        semivariance_asset(make_stock(), registry)
        assert registry.history.called

