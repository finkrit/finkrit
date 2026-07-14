# finkrit/tests/risk/test_valueatrisk.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finkritq.anal.risk.valueatrisk import (
    value_at_risk,
    value_at_risk_from_returns,
    value_at_risk_from_prices,
    portfolio_value_at_risk,
)
from packages.finkritq.datatype import VaREstimationMethod, ReturnCalculationMethod
from tests.fixtures import make_price_history

_RNG = np.random.default_rng(42)
_RETURNS_LARGE = _RNG.normal(0, 0.01, 500)
_PRICES_LARGE  = np.cumprod(1 + _RETURNS_LARGE) * 100


class TestVaRFromReturns:

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_positive_and_sensible(self, method):
        assert 0.0 < value_at_risk_from_returns(_RETURNS_LARGE, method=method) < 0.10

    def test_historical_consistent_across_calls(self):
        assert value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.HISTORICAL), abs=1e-12)

    def test_higher_confidence_gives_higher_var(self):
        assert value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.99) >= value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.95)

    def test_zero_returns_historical_give_zero_var(self):
        assert value_at_risk_from_returns(np.zeros(500), method=VaREstimationMethod.HISTORICAL) == pytest.approx(0.0)

    def test_zero_returns_parametric_give_zero_var(self):
        assert value_at_risk_from_returns(np.zeros(500), method=VaREstimationMethod.PARAMETRIC) == pytest.approx(0.0)

    def test_zero_returns_monte_carlo_give_zero_var(self):
        assert value_at_risk_from_returns(np.zeros(500), method=VaREstimationMethod.MONTE_CARLO, random_state=42) == pytest.approx(0.0)

    @pytest.mark.parametrize("confidence", [-0.1, 0.0, 1.0, 1.5])
    def test_invalid_confidence_raises(self, confidence):
        with pytest.raises(ValueError):
            value_at_risk_from_returns(_RETURNS_LARGE, confidence=confidence)

    def test_monte_carlo_reproducible(self):
        assert value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.MONTE_CARLO, random_state=42) == pytest.approx(value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.MONTE_CARLO, random_state=42))

    def test_monte_carlo_different_seed_differs(self):
        assert value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.MONTE_CARLO, random_state=1) != pytest.approx(value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.MONTE_CARLO, random_state=2))


class TestVaRFromPrices:

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_var_methods_positive(self, method):
        assert value_at_risk_from_prices(_PRICES_LARGE, method=method) > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods_positive(self, return_method):
        assert value_at_risk_from_prices(_PRICES_LARGE, return_method=return_method) > 0.0

    def test_matches_returns(self):
        from packages.finkritq.anal.returns import calculate_returns
        assert value_at_risk_from_prices(_PRICES_LARGE, method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_returns(calculate_returns(_PRICES_LARGE), method=VaREstimationMethod.HISTORICAL), rel=1e-9)

    def test_higher_confidence_gives_higher_var(self):
        assert value_at_risk_from_prices(_PRICES_LARGE, confidence=0.99) >= value_at_risk_from_prices(_PRICES_LARGE, confidence=0.95)


class TestVaRHistory:

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_methods_positive(self, method):
        assert value_at_risk(make_price_history(_PRICES_LARGE.tolist()), method=method) > 0.0

    def test_matches_from_prices(self):
        h = make_price_history(_PRICES_LARGE.tolist())
        assert value_at_risk(h, method=VaREstimationMethod.HISTORICAL) == pytest.approx(
            value_at_risk_from_prices(h.close, method=VaREstimationMethod.HISTORICAL), rel=1e-9
        )

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods_positive(self, return_method):
        assert value_at_risk(make_price_history(_PRICES_LARGE.tolist()), return_method=return_method) > 0.0

    def test_higher_confidence_gives_higher_var(self):
        h = make_price_history(_PRICES_LARGE.tolist())
        assert value_at_risk(h, confidence=0.99) >= value_at_risk(h, confidence=0.95)

    def test_monte_carlo_reproducible(self):
        h = make_price_history(_PRICES_LARGE.tolist())
        assert value_at_risk(h, method=VaREstimationMethod.MONTE_CARLO, random_state=7) == pytest.approx(
            value_at_risk(h, method=VaREstimationMethod.MONTE_CARLO, random_state=7)
        )


class TestPortfolioVaR:

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_positive(self, two_stock_portfolio_data, method):
        assert portfolio_value_at_risk(two_stock_portfolio_data, method=method) > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods_positive(self, two_stock_portfolio_data, return_method):
        assert portfolio_value_at_risk(two_stock_portfolio_data, return_method=return_method) > 0.0

    def test_higher_confidence_gives_higher_var(self, two_stock_portfolio_data):
        assert portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.99) >= portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.95)

    def test_matches_value_series(self, two_stock_portfolio_data):
        assert portfolio_value_at_risk(two_stock_portfolio_data, method=VaREstimationMethod.HISTORICAL) == pytest.approx(
            value_at_risk_from_prices(two_stock_portfolio_data.value, method=VaREstimationMethod.HISTORICAL), rel=1e-9
        )

    def test_monte_carlo_reproducible(self, two_stock_portfolio_data):
        v1 = portfolio_value_at_risk(two_stock_portfolio_data, method=VaREstimationMethod.MONTE_CARLO, random_state=99)
        v2 = portfolio_value_at_risk(two_stock_portfolio_data, method=VaREstimationMethod.MONTE_CARLO, random_state=99)
        assert v1 == pytest.approx(v2)

    def test_invalid_confidence_raises(self, two_stock_portfolio_data):
        with pytest.raises(ValueError):
            portfolio_value_at_risk(two_stock_portfolio_data, confidence=1.5)


    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_var_methods_positive(self, method):
        assert value_at_risk(make_price_history(_PRICES_LARGE.tolist()), method=method) > 0.0

    def test_matches_from_prices(self):
        h = make_price_history(_PRICES_LARGE.tolist())
        assert value_at_risk(h, method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_prices(h.close, method=VaREstimationMethod.HISTORICAL), rel=1e-9)

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, return_method):
        assert value_at_risk(make_price_history(_PRICES_LARGE.tolist()), return_method=return_method) > 0.0


class TestPortfolioVaR:

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_positive(self, two_stock_portfolio_data, method):
        assert portfolio_value_at_risk(two_stock_portfolio_data, method=method) > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, return_method):
        assert portfolio_value_at_risk(two_stock_portfolio_data, return_method=return_method) > 0.0

    def test_confidence_increases_var(self, two_stock_portfolio_data):
        assert portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.99) >= portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.95)

    def test_matches_value_series(self, two_stock_portfolio_data):
        assert portfolio_value_at_risk(two_stock_portfolio_data, method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_prices(two_stock_portfolio_data.value, method=VaREstimationMethod.HISTORICAL), rel=1e-9)

