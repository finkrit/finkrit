# finkrit/tests/risk/test_beta.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.anal.risk.beta import (
    beta,
    beta_from_prices,
    beta_from_returns,
)
from packages.finq.datatype import ReturnCalculationMethod
from tests.fixtures import make_price_history, MARKET_PRICES
from tests.risk.conftest import RETURNS_A, RETURNS_B, PRICES


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


class TestBetaFromPrices:

    def test_self_beta_is_one(self):
        assert beta_from_prices(PRICES, PRICES) == pytest.approx(1.0, abs=1e-9)

    def test_simple_method(self):
        b = beta_from_prices(PRICES, PRICES, method=ReturnCalculationMethod.SIMPLE)
        assert b == pytest.approx(1.0, abs=1e-9)


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
