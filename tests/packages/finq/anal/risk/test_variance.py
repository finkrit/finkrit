# finkrit/tests/risk/test_variance.py
from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from packages.finkritq.anal.risk.variance import (
    variance_from_returns,
    variance_from_prices,
    variance,
    variance_asset,
    portfolio_variance)
from packages.finkritq.anal.returns import calculate_returns
from tests.fixtures import make_price_history, make_stock
from tests.fixtures import RETURNS_A, PRICES, FLAT_PRICES


class TestVarianceFromReturns:

    def test_matches_numpy_var(self):
        expected = np.var(RETURNS_A, ddof=1)
        actual = variance_from_returns(RETURNS_A, annualized=False)
        assert actual == pytest.approx(expected)

    def test_non_negative_result(self):
        assert variance_from_returns(RETURNS_A) >= 0.0

    def test_zero_for_flat_returns(self):
        assert variance_from_returns(np.zeros(20), annualized=False) == pytest.approx(0.0, abs=1e-12)

    def test_annualized_equals_daily_times_252(self):
        daily  = variance_from_returns(RETURNS_A, annualized=False)
        annual = variance_from_returns(RETURNS_A, annualized=True)
        assert annual == pytest.approx(daily * 252, rel=1e-9)

    def test_constant_returns_have_zero_variance(self):
        returns = np.full(30, 0.015)

        assert variance_from_returns(
            returns,
            annualized=False,
        ) == pytest.approx(0.0)

    def test_scaling_returns_scales_variance(self):
        base = variance_from_returns(RETURNS_A, annualized=False)
        scaled = variance_from_returns(RETURNS_A * 2, annualized=False)

        assert scaled == pytest.approx(base * 4)

    def test_shifting_returns_does_not_change_variance(self):
        base = variance_from_returns(RETURNS_A, annualized=False)
        shifted = variance_from_returns(RETURNS_A + 0.05, annualized=False)

        assert shifted == pytest.approx(base)

    def test_order_does_not_change_variance(self):
        reversed_returns = RETURNS_A[::-1]

        expected = variance_from_returns(RETURNS_A, annualized=False)

        actual = variance_from_returns(reversed_returns, annualized=False)

        assert actual == pytest.approx(expected)

    def test_custom_periods_per_year(self):
        daily = variance_from_returns(RETURNS_A, annualized=False)
        annual = variance_from_returns(RETURNS_A, annualized=True, periods_per_year=365)

        assert annual == pytest.approx(daily * 365)


class TestVarianceFromPrices:

    def test_non_negative_prices(self):
        assert variance_from_prices(PRICES) >= 0.0

    def test_consistent_with_returns_version(self):
        returns = calculate_returns(PRICES)
        v_prices  = variance_from_prices(PRICES,   annualized=False)
        v_returns = variance_from_returns(returns, annualized=False)
        assert v_prices == pytest.approx(v_returns, rel=1e-9)

    def test_flat_prices_have_zero_variance(self):
        assert variance_from_prices(FLAT_PRICES, annualized=False) == pytest.approx(0.0)

    def test_matches_numpy_prices(self):
        returns = calculate_returns(PRICES)
        expected = np.var(returns, ddof=1)
        actual = variance_from_prices(PRICES, annualized=False)
        assert actual == pytest.approx(expected)


class TestVarianceAsset:

    def _make_registry(self, history):
        registry = MagicMock()
        registry.history.return_value = history
        return registry

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        result = variance_asset(make_stock(), self._make_registry(h))
        assert isinstance(result, float)

    def test_non_negative(self):
        h = make_price_history(PRICES.tolist())
        assert variance_asset(make_stock(), self._make_registry(h)) >= 0.0

    def test_matches_history_version(self):
        h = make_price_history(PRICES.tolist())
        assert variance_asset(make_stock(), self._make_registry(h), annualized=False) == pytest.approx(variance(h, annualized=False), rel=1e-9)

    def test_calls_registry_history(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        variance_asset(make_stock(), registry)
        assert registry.history.called


class TestVarianceHistory:

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        result = variance(h)
        assert isinstance(result, float)

    def test_matches_price_version(self):
        history = make_price_history(PRICES)
        expected = variance_from_prices(PRICES, annualized=False)
        actual = variance(history, annualized=False)

        assert actual == pytest.approx(expected)


class TestPortfolioVariance:

    def test_positive(self, two_stock_portfolio_data):
        pv = portfolio_variance(two_stock_portfolio_data)
        assert pv > 0.0

    def test_scalar(self, two_stock_portfolio_data):
        pv = portfolio_variance(two_stock_portfolio_data)
        assert np.isscalar(pv) or pv.ndim == 0

    @patch("packages.finkritq.anal.risk.variance.covariance_matrix")
    def test_identity_covariance(self, mock_covariance, two_stock_portfolio_data):
        mock_covariance.return_value = np.eye(2)
        weights = two_stock_portfolio_data.weight_vector
        expected = np.sum(weights ** 2)
        actual = portfolio_variance(two_stock_portfolio_data)

        assert actual == pytest.approx(expected)

    @patch("packages.finkritq.anal.risk.variance.covariance_matrix")
    def test_zero_covariance(self, mock_covariance, two_stock_portfolio_data):
        mock_covariance.return_value = np.zeros((2, 2))

        assert portfolio_variance(two_stock_portfolio_data) == pytest.approx(0.0)

    @patch("packages.finkritq.anal.risk.variance.covariance_matrix")
    def test_matches_manual_matrix_calculation(self, mock_covariance, two_stock_portfolio_data):
        covariance = np.array(
            [
                [0.04, 0.01],
                [0.01, 0.09],
            ]
        )

        mock_covariance.return_value = covariance
        weights = two_stock_portfolio_data.weight_vector
        expected = float(weights.T @ covariance @ weights)
        actual = portfolio_variance(two_stock_portfolio_data)

        assert actual == pytest.approx(expected)

