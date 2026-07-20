# finkrit/tests/risk/test_covariance.py
from __future__ import annotations

import numpy as np
import pytest

from unittest.mock import MagicMock

from finkritq.anal.risk.covariance import (
    covariance_from_returns,
    covariance_from_prices,
    covariance_matrix,
    covariance_matrix_from_returns,
    covariance_assets,
)
from finkritq.anal.risk.covariance import covariance
from finkritq.transform.returns import periodic_returns
from finkritq.tests.fixtures import make_price_history, make_stock, make_price_history
from finkritq.tests.fixtures import RETURNS_A, RETURNS_B, PRICES


class TestCovarianceFromReturns:

    def test_covariance_of_self_equals_variance(self):
        cov = covariance_from_returns(RETURNS_A, RETURNS_A, annualized=False)
        var = np.var(RETURNS_A, ddof=1)
        assert cov == pytest.approx(var, abs=1e-10)

    def test_symmetry(self):
        c_ab = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        c_ba = covariance_from_returns(RETURNS_B, RETURNS_A, annualized=False)
        assert c_ab == pytest.approx(c_ba, abs=1e-12)

    def test_annualized_larger_than_daily(self):
        daily  = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        annual = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=True)
        assert abs(annual) > abs(daily)

    def test_matches_numpy_ddof1(self):
        expected = np.cov(RETURNS_A, RETURNS_B, ddof=1)[0, 1]
        actual = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        assert actual == pytest.approx(expected)

    def test_zero_for_constant_series(self):
        returns = np.full(20, 0.01)
        assert covariance_from_returns(returns, returns, annualized=False) == pytest.approx(0.0)

    def test_scaling_one_series_scales_covariance(self):
        base = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        scaled = covariance_from_returns(2 * RETURNS_A, RETURNS_B, annualized=False)

        assert scaled == pytest.approx(2 * base)

    def test_scaling_both_series_scales_covariance(self):
        base = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        scaled = covariance_from_returns(2 * RETURNS_A, 3 * RETURNS_B, annualized=False)

        assert scaled == pytest.approx(6 * base)

    def test_shifting_returns_does_not_change_covariance(self):
        base = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        shifted = covariance_from_returns(RETURNS_A + 0.05, RETURNS_B - 0.02, annualized=False)

        assert shifted == pytest.approx(base)

    def test_custom_periods_per_year(self):
        daily = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=False)
        annual = covariance_from_returns(RETURNS_A, RETURNS_B, annualized=True, periods_per_year=365)

        assert annual == pytest.approx(daily * 365)


class TestCovarianceFromPrices:

    def test_self_covariance_positive(self):
        assert covariance_from_prices(PRICES, PRICES, annualized=False) >= 0.0

    def test_matches_returns_version(self):
        returns = periodic_returns(PRICES)
        assert covariance_from_prices(PRICES, PRICES, annualized=False) == pytest.approx(covariance_from_returns(returns, returns, annualized=False))

    def test_matches_numpy_cov(self):
        returns = periodic_returns(PRICES)
        expected = np.cov(returns, returns, ddof=1)[0, 1]
        assert covariance_from_prices(PRICES, PRICES, annualized=False) == pytest.approx(expected)


class TestCovarianceMatrix:

    def test_matrix_shape(self, two_stock_portfolio_data):
        mat = covariance_matrix(two_stock_portfolio_data)
        n = two_stock_portfolio_data.n_assets
        assert mat.shape == (n, n)

    def test_matrix_symmetric(self, two_stock_portfolio_data):
        mat = covariance_matrix(two_stock_portfolio_data)
        np.testing.assert_allclose(mat, mat.T, atol=1e-12)

    def test_diagonal_non_negative(self, two_stock_portfolio_data):
        mat = covariance_matrix(two_stock_portfolio_data)
        assert np.all(np.diag(mat) >= 0.0)

    def test_matches_price_version(self):
        history = make_price_history(PRICES)

        assert covariance(history, history, annualized=False) == pytest.approx(
            covariance_from_prices(PRICES, PRICES, annualized=False)
        )

    def test_matches_numpy_cov_matrix(self, two_stock_portfolio_data):
        returns = two_stock_portfolio_data.return_matrix()
        np.testing.assert_allclose(
            covariance_matrix(two_stock_portfolio_data, annualized=False),
            np.cov(returns, rowvar=True, ddof=1),
        )

    def test_annualization(self, two_stock_portfolio_data):
        daily = covariance_matrix(two_stock_portfolio_data, annualized=False)
        annual = covariance_matrix(two_stock_portfolio_data, annualized=True)

        np.testing.assert_allclose(annual, daily * 252)

    def test_positive_semidefinite(self, two_stock_portfolio_data):
        eigenvalues = np.linalg.eigvalsh(covariance_matrix(two_stock_portfolio_data, annualized=False))
        assert np.all(eigenvalues >= -1e-12)


class TestCovarianceMatrixFromReturns:

    def test_shape(self):
        returns = np.vstack([RETURNS_A, RETURNS_B])
        mat = covariance_matrix_from_returns(returns, annualized=False)
        assert mat.shape == (2, 2)

    def test_symmetric(self):
        returns = np.vstack([RETURNS_A, RETURNS_B])
        mat = covariance_matrix_from_returns(returns, annualized=False)
        np.testing.assert_allclose(mat, mat.T, atol=1e-12)

    def test_matches_numpy(self):
        returns = np.vstack([RETURNS_A, RETURNS_B])
        np.testing.assert_allclose(
            covariance_matrix_from_returns(returns, annualized=False),
            np.cov(returns, rowvar=True, ddof=1),
        )

    def test_annualization(self):
        returns = np.vstack([RETURNS_A, RETURNS_B])
        daily = covariance_matrix_from_returns(returns, annualized=False)
        annual = covariance_matrix_from_returns(returns, annualized=True)
        np.testing.assert_allclose(annual, daily * 252)


class TestCovarianceAssets:

    def _make_registry(self, history):
        registry = MagicMock()
        registry.history.return_value = history
        return registry

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        stock = make_stock()
        result = covariance_assets(stock, stock, registry)
        assert isinstance(result, float)

    def test_self_covariance_positive(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        stock = make_stock()
        assert covariance_assets(stock, stock, registry) > 0.0

    def test_calls_registry_history(self):
        h = make_price_history(PRICES.tolist())
        registry = self._make_registry(h)
        stock = make_stock()
        covariance_assets(stock, stock, registry)
        assert registry.history.called

