# finkrit/tests/risk/test_correlation.py
from __future__ import annotations

import numpy as np
import pytest


from packages.finq.anal.risk.correlation import (
     correlation,
    correlation_from_returns,
    correlation_from_prices,
    correlation_matrix,

    )
from packages.finq.datatype import ReturnCalculationMethod
from tests.fixtures import make_price_history, RETURNS_A, RETURNS_B, PRICES


class TestCorrelationFromReturns:

    def test_self_correlation_is_one(self):
        corr = correlation_from_returns(RETURNS_A, RETURNS_A)
        assert corr == pytest.approx(1.0, abs=1e-9)

    def test_range(self):
        corr = correlation_from_returns(RETURNS_A, RETURNS_B)
        assert -1.0 <= corr <= 1.0

    def test_symmetry(self):
        c_ab = correlation_from_returns(RETURNS_A, RETURNS_B)
        c_ba = correlation_from_returns(RETURNS_B, RETURNS_A)
        assert c_ab == pytest.approx(c_ba, abs=1e-12)

    def test_opposite_series_negative(self):
        corr = correlation_from_returns(RETURNS_A, -RETURNS_A)
        assert corr == pytest.approx(-1.0, abs=1e-9)

    def test_linear_scaling_preserves_correlation(self):
        corr = correlation_from_returns(RETURNS_A, RETURNS_B)
        scaled = correlation_from_returns(5.0 * RETURNS_A, 10.0 * RETURNS_B)
        assert scaled == pytest.approx(corr, abs=1e-12)

    def test_translation_preserves_correlation(self):
        corr = correlation_from_returns(RETURNS_A, RETURNS_B)
        shifted = correlation_from_returns(RETURNS_A + 1.0, RETURNS_B - 2.0)
        assert shifted == pytest.approx(corr, abs=1e-12)


class TestCorrelationHistory:

    def test_matches_prices(self):
        h1 = make_price_history(PRICES.tolist())
        h2 = make_price_history((PRICES * 1.1).tolist())
        assert correlation(h1, h2) == pytest.approx(
            correlation_from_prices(h1.close, h2.close),
            abs=1e-12,
        )

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        h1 = make_price_history(PRICES.tolist())
        h2 = make_price_history((PRICES * 1.1).tolist())
        assert -1.0 <= correlation(h1, h2, method=method) <= 1.0


class TestCorrelationFromPrices:

    def test_self_is_one(self):
        assert correlation_from_prices(PRICES, PRICES) == pytest.approx(1.0, abs=1e-9)

    def test_scale_invariant(self):
        corr = correlation_from_prices(PRICES, PRICES * 1.1)
        scaled = correlation_from_prices(PRICES * 100.0, PRICES * 250.0)
        assert scaled == pytest.approx(corr, abs=1e-12)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        corr = correlation_from_prices(PRICES, PRICES, method=method)
        assert corr == pytest.approx(1.0, abs=1e-9)


class TestCorrelationMatrix:

    def test_shape(self, two_stock_portfolio_data):
        mat = correlation_matrix(two_stock_portfolio_data)
        n = two_stock_portfolio_data.n_assets
        assert mat.shape == (n, n)

    def test_diagonal_is_one(self, two_stock_portfolio_data):
        mat = correlation_matrix(two_stock_portfolio_data)
        np.testing.assert_allclose(np.diag(mat), 1.0, atol=1e-9)

    def test_values_in_range(self, two_stock_portfolio_data):
        mat = correlation_matrix(two_stock_portfolio_data)
        assert np.all(mat >= -1.0)
        assert np.all(mat <= 1.0)

    def test_symmetric(self, two_stock_portfolio_data):
        mat = correlation_matrix(two_stock_portfolio_data)
        np.testing.assert_allclose(mat, mat.T, atol=1e-12)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, method):
        mat = correlation_matrix(two_stock_portfolio_data, method=method)
        np.testing.assert_allclose(np.diag(mat), 1.0, atol=1e-9)