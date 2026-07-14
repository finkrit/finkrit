# finkrit/tests/risk/test_beta.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finkritq.anal.risk.beta import (
    beta,
    beta_from_prices,
    beta_from_returns,
)
from packages.finkritq.datatype import ReturnCalculationMethod
from tests.fixtures import make_price_history, MARKET_PRICES
from tests.fixtures import RETURNS_A, RETURNS_B, PRICES


class TestBetaFromReturns:

    def test_beta_of_self_is_one(self):
        assert beta_from_returns(RETURNS_A, RETURNS_A) == pytest.approx(1.0, abs=1e-9)

    def test_known_multiple(self):
        # RETURNS_B = 1.5 × RETURNS_A → β ≈ 1.5
        assert beta_from_returns(RETURNS_B, RETURNS_A) == pytest.approx(1.5, abs=1e-6)

    def test_zero_market_variance_returns_nan(self):
        assert np.isnan(beta_from_returns(RETURNS_A, np.zeros(len(RETURNS_A))))

    def test_result_is_float(self):
        assert isinstance(beta_from_returns(RETURNS_A, RETURNS_B), float)

    def test_negative_multiple(self):
        assert beta_from_returns(-RETURNS_A, RETURNS_A) == pytest.approx(-1.0, abs=1e-9)

    def test_zero_asset_returns(self):
        assert beta_from_returns(np.zeros(len(RETURNS_A)), RETURNS_A) == pytest.approx(0.0, abs=1e-9)

    def test_constant_offset_does_not_change_beta(self):
        assert beta_from_returns(RETURNS_A + 5.0, RETURNS_A) == pytest.approx(1.0, abs=1e-9)

    def test_scaling_market_changes_beta_inverse(self):
        assert beta_from_returns(RETURNS_A, RETURNS_A * 2.0) == pytest.approx(0.5, abs=1e-9)

    def test_scaling_both_series_keeps_beta(self):
        assert beta_from_returns(RETURNS_A * 3.0, RETURNS_A * 3.0) == pytest.approx(1.0, abs=1e-9)

    def test_single_observation_returns_nan(self):
        assert np.isnan(beta_from_returns(np.array([1.0]), np.array([1.0])))


class TestBetaFromPrices:

    def test_self_beta_is_one(self):
        assert beta_from_prices(PRICES, PRICES) == pytest.approx(1.0, abs=1e-9)

    def test_simple_method(self):
        b = beta_from_prices(PRICES, PRICES, method=ReturnCalculationMethod.SIMPLE)
        assert b == pytest.approx(1.0, abs=1e-9)

    def test_scaled_prices_have_same_beta(self):
        assert beta_from_prices(PRICES * 10.0, PRICES * 100.0) == pytest.approx(1.0, abs=1e-9)

    def test_constant_asset_prices_give_zero_beta(self):
        # flat asset → zero covariance with anything → beta = 0.0
        b = beta_from_prices(np.ones(10), PRICES[:10])
        assert b == pytest.approx(0.0, abs=1e-9)

    def test_both_constant_price_series_return_nan(self):
        assert np.isnan(beta_from_prices(np.ones(10), np.ones(10)))

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods_self_beta_is_one(self, method):
        assert beta_from_prices(PRICES, PRICES, method=method) == pytest.approx(1.0, abs=1e-9)


class TestBeta:

    def test_beta_history_self(self):
        h = make_price_history(MARKET_PRICES)
        assert beta(h, h) == pytest.approx(1.0, abs=1e-9)

    def test_beta_aligns_different_length_histories(self):
        h_long  = make_price_history(MARKET_PRICES, start="2024-01-01")
        h_short = make_price_history(MARKET_PRICES[2:], start="2024-01-03")
        # should not raise
        result = beta(h_long, h_short)
        assert np.isfinite(result)

    def test_beta_is_symmetric_for_identical_histories(self):
        h = make_price_history(MARKET_PRICES); assert beta(h, h) == pytest.approx(beta(h, h), abs=1e-9)

    def test_beta_with_simple_returns(self):
        h = make_price_history(MARKET_PRICES); assert beta(h, h, method=ReturnCalculationMethod.SIMPLE) == pytest.approx(1.0, abs=1e-9)

    def test_alignment_order_does_not_matter(self):
        h1 = make_price_history(MARKET_PRICES, start="2024-01-01"); h2 = make_price_history(MARKET_PRICES[2:], start="2024-01-03"); assert np.isfinite(beta(h2, h1))

