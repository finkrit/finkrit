# finkrit/tests/packages/finkritq/anal/risk/test_conditionalvalueatrisk.py
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.conditionalvalueatrisk import (
    conditional_value_at_risk,
    conditional_value_at_risk_from_returns,
    conditional_value_at_risk_from_prices,
    portfolio_conditional_value_at_risk,
)
from finkritq.anal.risk.valueatrisk import (
    value_at_risk_from_returns,
    value_at_risk_from_prices,
)
from finkritq.datatype import (
    ReturnCalculationMethod,
    VaREstimationMethod,
)
from finkritq.tests.fixtures import make_price_history

_RNG = np.random.default_rng(0)
_RETURNS_LARGE = _RNG.normal(0, 0.01, 500)


class TestCVaRFromReturns:

    @pytest.mark.parametrize("method", [
        VaREstimationMethod.HISTORICAL,
        VaREstimationMethod.PARAMETRIC,
        VaREstimationMethod.MONTE_CARLO,
    ])
    def test_cvar_ge_var(self, method):
        var = value_at_risk_from_returns(_RETURNS_LARGE, method=method)
        cvar = conditional_value_at_risk_from_returns(_RETURNS_LARGE, method=method)
        assert cvar >= var - 1e-10

    def test_positive(self):
        assert conditional_value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.HISTORICAL,
        ) > 0.0

    def test_higher_confidence_gives_higher_cvar(self):
        c95 = conditional_value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.95)
        c99 = conditional_value_at_risk_from_returns(_RETURNS_LARGE, confidence=0.99)
        assert c99 >= c95

    def test_zero_returns(self):
        returns = np.zeros(500)

        assert conditional_value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.HISTORICAL,
        ) == pytest.approx(0.0)

        assert conditional_value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.PARAMETRIC,
        ) == pytest.approx(0.0)

        assert conditional_value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        ) == pytest.approx(0.0)

    @pytest.mark.parametrize("confidence", [-0.1, 0.0, 1.0, 1.5])
    def test_invalid_confidence(self, confidence):
        with pytest.raises(ValueError):
            conditional_value_at_risk_from_returns(
                _RETURNS_LARGE,
                confidence=confidence,
            )

    def test_monte_carlo_reproducible(self):
        c1 = conditional_value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        )

        c2 = conditional_value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=42,
        )

        assert c1 == pytest.approx(c2)

    def test_monte_carlo_different_seed(self):
        c1 = conditional_value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=1,
        )

        c2 = conditional_value_at_risk_from_returns(
            _RETURNS_LARGE,
            method=VaREstimationMethod.MONTE_CARLO,
            random_state=2,
        )

        assert c1 != pytest.approx(c2)


class TestCVaRFromPrices:

    def test_positive_prices(self):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        assert conditional_value_at_risk_from_prices(prices) > 0.0

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_cvar_methods(self, method):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        assert conditional_value_at_risk_from_prices(prices, method=method) > 0.0

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, return_method):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        assert conditional_value_at_risk_from_prices(prices, return_method=return_method) > 0.0

    def test_matches_returns(self):
        from finkritq.transform.returns import periodic_returns

        prices = np.cumprod(1 + _RETURNS_LARGE) * 100
        returns = periodic_returns(prices)

        assert conditional_value_at_risk_from_prices(
            prices,
            method=VaREstimationMethod.HISTORICAL,
        ) == pytest.approx(
            conditional_value_at_risk_from_returns(
                returns,
                method=VaREstimationMethod.HISTORICAL,
            ),
            rel=1e-9,
        )

    def test_cvar_ge_var(self):
        prices = np.cumprod(1 + _RETURNS_LARGE) * 100

        var = value_at_risk_from_prices(prices)
        cvar = conditional_value_at_risk_from_prices(prices)

        assert cvar >= var


class TestCVaRHistory:

    def test_matches_prices(self):
        history = make_price_history((np.cumprod(1 + _RETURNS_LARGE) * 100).tolist())

        assert conditional_value_at_risk(
            history,
            method=VaREstimationMethod.HISTORICAL,
        ) == pytest.approx(
            conditional_value_at_risk_from_prices(
                history.close,
                method=VaREstimationMethod.HISTORICAL,
            ),
            rel=1e-9,
        )

    @pytest.mark.parametrize("method", list(VaREstimationMethod))
    def test_all_methods(self, method):
        history = make_price_history((np.cumprod(1 + _RETURNS_LARGE) * 100).tolist())
        assert conditional_value_at_risk(history, method=method) > 0.0



class TestPortfolioCVaR:

    @pytest.mark.parametrize("method", [
        VaREstimationMethod.HISTORICAL,
        VaREstimationMethod.PARAMETRIC,
        VaREstimationMethod.MONTE_CARLO,
    ])
    def test_positive(self, two_stock_portfolio_data, method):
        assert portfolio_conditional_value_at_risk(two_stock_portfolio_data, method=method) > 0.0

    def test_cvar_ge_var(self, two_stock_portfolio_data):
        from finkritq.anal.risk.valueatrisk import portfolio_value_at_risk

        var = portfolio_value_at_risk(two_stock_portfolio_data)
        cvar = portfolio_conditional_value_at_risk(two_stock_portfolio_data)

        assert cvar >= var - 1e-10

    @pytest.mark.parametrize("return_method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, return_method):
        assert portfolio_conditional_value_at_risk(
            two_stock_portfolio_data,
            return_method=return_method,
        ) > 0.0

    def test_confidence_increases_cvar(self, two_stock_portfolio_data):
        c95 = portfolio_conditional_value_at_risk(two_stock_portfolio_data, confidence=0.95)
        c99 = portfolio_conditional_value_at_risk(two_stock_portfolio_data, confidence=0.99)

        assert c99 >= c95

        