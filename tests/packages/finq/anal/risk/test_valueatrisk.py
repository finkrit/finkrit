# finkrit/tests/risk/test_valueatrisk.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.anal.risk.valueatrisk import (
    value_at_risk,
    value_at_risk_from_returns,
    value_at_risk_from_prices,
    portfolio_value_at_risk,
)
from packages.finq.datatype import VaREstimationMethod, ReturnCalculationMethod
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
        from packages.finq.anal.returns import calculate_returns
        assert value_at_risk_from_prices(_PRICES_LARGE, method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_returns(calculate_returns(_PRICES_LARGE), method=VaREstimationMethod.HISTORICAL), rel=1e-9)

    def test_higher_confidence_gives_higher_var(self):
        assert value_at_risk_from_prices(_PRICES_LARGE, confidence=0.99) >= value_at_risk_from_prices(_PRICES_LARGE, confidence=0.95)


class TestVaRHistory:

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



class TestVaRFromReturns:

    @pytest.mark.parametrize("method", [
        VaREstimationMethod.HISTORICAL,
        VaREstimationMethod.PARAMETRIC,
        VaREstimationMethod.MONTE_CARLO,
    ])
    def test_positive_and_sensible(self, method):
        var = value_at_risk_from_returns(_RETURNS_LARGE, method=method)
        assert 0.0 < var < 0.10

    def test_historical_consistent_across_calls(self):
        v1 = value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.HISTORICAL)
        v2 = value_at_risk_from_returns(_RETURNS_LARGE, method=VaREstimationMethod.HISTORICAL)
        assert v1 == pytest.approx(v2, abs=1e-12)

    def test_higher_confidence_gives_higher_var(self):
        v95 = value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.95)
        v99 = value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.99)
        assert v99 >= v95

    def test_zero_returns_give_zero_var(self):
        returns = np.zeros(500)

        assert value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.HISTORICAL,
        ) == pytest.approx(0.0)

        assert value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.PARAMETRIC,
        ) == pytest.approx(0.0)

        assert value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        ) == pytest.approx(0.0)

    @pytest.mark.parametrize("confidence", [-0.1, 0.0, 1.0, 1.5])
    def test_invalid_confidence(self, confidence):
        with pytest.raises(ValueError):
            value_at_risk_from_returns(_RETURNS_LARGE, confidence=confidence)

    def test_monte_carlo_reproducible(self):
        v1 = value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        )

        v2 = value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        )

        assert v1 == pytest.approx(v2)

    def test_monte_carlo_different_seed(self):
        v1 = value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=1,
        )

        v2 = value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=2,
        )

        assert v1 != pytest.approx(v2)


class TestVaRFromPrices:

    def test_positive(self):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        var = value_at_risk_from_prices(prices)
        assert var > 0.0

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_var_methods(self, method):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        assert value_at_risk_from_prices(prices, method=method) > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, return_method):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        assert value_at_risk_from_prices(prices,return_method=return_method) > 0.0

    def test_matches_returns(self):
        from packages.finq.anal.returns import calculate_returns

        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        returns = calculate_returns(prices)

        assert value_at_risk_from_prices(
            prices,
            method=VaREstimationMethod.HISTORICAL) == pytest.approx(value_at_risk_from_returns(returns, method=VaREstimationMethod.HISTORICAL), rel=1e-9)

class TestPortfolioVaR:

    @pytest.mark.parametrize("method", [
        VaREstimationMethod.HISTORICAL,
        VaREstimationMethod.PARAMETRIC,
        VaREstimationMethod.MONTE_CARLO,
    ])
    def test_positive(self, two_stock_portfolio_data, method):
        var = portfolio_value_at_risk(two_stock_portfolio_data, method=method)
        assert var > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, return_method):
        assert portfolio_value_at_risk(two_stock_portfolio_data, return_method=return_method) > 0.0

    def test_confidence_increases_var(self, two_stock_portfolio_data):
        v95 = portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.95)

        v99 = portfolio_value_at_risk(two_stock_portfolio_data, confidence=0.99)

        assert v99 >= v95


class TestVaRHistory:

    def test_matches_prices(self):
        history = make_price_history((np.cumprod(1 + _RETURNS_LARGE) * 100).tolist())

        assert value_at_risk(
            history,
            method=VaREstimationMethod.HISTORICAL,
        ) == pytest.approx(
            value_at_risk_from_prices(
                history.close,
                method=VaREstimationMethod.HISTORICAL,
            ),
            rel=1e-9,
        )

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_var_methods(self, method):
        history = make_price_history((np.cumprod(1 + _RETURNS_LARGE) * 100).tolist())
        assert value_at_risk(history, method=method) > 0.0