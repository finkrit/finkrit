# finkrit/tests/packages/finkritq/anal/returns/test_returns.py
"""
Tests for packages.finkritq.anal.returns — calculate_returns().
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.returns import calculate_returns
from finkritq.datatype import ReturnCalculationMethod
from finkritq.tests.fixtures import (
    FLAT_PRICES,
    RISING_PRICES,
    MARKET_PRICES,
    RETURNS_A,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_returns(prices: np.ndarray) -> np.ndarray:
    return (prices[1:] / prices[:-1]) - 1


def _log_returns(prices: np.ndarray) -> np.ndarray:
    return np.diff(np.log(prices))


# ---------------------------------------------------------------------------
# Length / shape
# ---------------------------------------------------------------------------

class TestReturnLength:

    def test_log_length_is_n_minus_1(self):
        r = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.LOG)
        assert len(r) == len(MARKET_PRICES) - 1

    def test_simple_length_is_n_minus_1(self):
        r = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.SIMPLE)
        assert len(r) == len(MARKET_PRICES) - 1

    def test_two_prices_gives_one_return(self):
        r = calculate_returns(np.array([100.0, 110.0]))
        assert len(r) == 1

    def test_returns_1d_array(self):
        r = calculate_returns(MARKET_PRICES)
        assert r.ndim == 1


# ---------------------------------------------------------------------------
# Exact numerical values
# ---------------------------------------------------------------------------

class TestLogReturnValues:

    def test_known_doubling(self):
        # ln(200/100) = ln(2)
        r = calculate_returns(np.array([100.0, 200.0]), ReturnCalculationMethod.LOG)
        assert r[0] == pytest.approx(np.log(2))

    def test_known_halving(self):
        r = calculate_returns(np.array([100.0, 50.0]), ReturnCalculationMethod.LOG)
        assert r[0] == pytest.approx(-np.log(2))

    def test_matches_numpy_diff_log(self):
        r = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.LOG)
        expected = _log_returns(MARKET_PRICES)
        np.testing.assert_allclose(r, expected, rtol=1e-12)

    def test_flat_prices_zero_returns(self):
        r = calculate_returns(FLAT_PRICES, ReturnCalculationMethod.LOG)
        np.testing.assert_allclose(r, 0.0, atol=1e-12)

    def test_consistent_with_fixtures_RETURNS_A(self):
        # RETURNS_A in fixtures.py is np.diff(np.log(MARKET_PRICES))
        r = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.LOG)
        np.testing.assert_allclose(r, RETURNS_A, rtol=1e-12)


class TestSimpleReturnValues:

    def test_ten_percent_gain(self):
        r = calculate_returns(np.array([100.0, 110.0]), ReturnCalculationMethod.SIMPLE)
        assert r[0] == pytest.approx(0.10)

    def test_twenty_percent_loss(self):
        r = calculate_returns(np.array([100.0, 80.0]), ReturnCalculationMethod.SIMPLE)
        assert r[0] == pytest.approx(-0.20)

    def test_matches_manual_formula(self):
        r = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.SIMPLE)
        expected = _simple_returns(MARKET_PRICES)
        np.testing.assert_allclose(r, expected, rtol=1e-12)

    def test_flat_prices_zero_returns(self):
        r = calculate_returns(FLAT_PRICES, ReturnCalculationMethod.SIMPLE)
        np.testing.assert_allclose(r, 0.0, atol=1e-12)


# ---------------------------------------------------------------------------
# Default method
# ---------------------------------------------------------------------------

class TestDefaultMethod:

    def test_default_is_log(self):
        default = calculate_returns(MARKET_PRICES)
        explicit = calculate_returns(MARKET_PRICES, ReturnCalculationMethod.LOG)
        np.testing.assert_array_equal(default, explicit)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unsupported_method_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            calculate_returns(MARKET_PRICES, method="bad_method")  # type: ignore


# ---------------------------------------------------------------------------
# Properties of returns
# ---------------------------------------------------------------------------

class TestReturnProperties:

    def test_rising_prices_all_positive_simple(self):
        r = calculate_returns(RISING_PRICES, ReturnCalculationMethod.SIMPLE)
        assert np.all(r > 0)

    def test_rising_prices_all_positive_log(self):
        r = calculate_returns(RISING_PRICES, ReturnCalculationMethod.LOG)
        assert np.all(r > 0)

    def test_returns_finite(self):
        r = calculate_returns(MARKET_PRICES)
        assert np.all(np.isfinite(r))

    def test_log_approx_simple_for_small_returns(self):
        """For small returns, log ≈ simple."""
        prices = 100.0 + np.arange(10, dtype=np.float64) * 0.01  # tiny moves
        log_r    = calculate_returns(prices, ReturnCalculationMethod.LOG)
        simple_r = calculate_returns(prices, ReturnCalculationMethod.SIMPLE)
        np.testing.assert_allclose(log_r, simple_r, rtol=1e-3)
