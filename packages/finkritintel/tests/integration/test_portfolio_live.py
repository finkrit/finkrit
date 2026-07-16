# finkritintel/tests/integration/test_portfolio_live.py
"""
Integration tests for finkritintel.integration.finq.portfolio_live.
Uses a mock DataRegistry — no network calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from finkritintel.integration.finkritq.portfolio_live import (
    PORTFOLIO_BETA_LIVE_BINDING,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_LIVE_BINDING,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING,
    PORTFOLIO_DOWNSIDE_DEVIATION_LIVE_BINDING,
    PORTFOLIO_DRAWDOWN_LIVE_BINDING,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_LIVE_BINDING,
    PORTFOLIO_MAXIMUM_DRAWDOWN_LIVE_BINDING,
    PORTFOLIO_SEMIVARIANCE_LIVE_BINDING,
    PORTFOLIO_VALUE_AT_RISK_LIVE_BINDING,
    PORTFOLIO_VARIANCE_LIVE_BINDING,
    PORTFOLIO_VOLATILITY_LIVE_BINDING,
)
from finkritintel.integration.finkritq.portfolio import (
    PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING,
    PORTFOLIO_VARIANCE_BINDING,
    PORTFOLIO_VOLATILITY_BINDING,
)

from .fixtures import BENCHMARK_HISTORY, make_portfolio_data


def _make_portfolio_registry(portfolio_data):
    registry = MagicMock()
    registry.history.side_effect = lambda target, **_: portfolio_data[target]
    return registry


class TestPortfolioLiveBindingContracts:
    """Live bindings reference the same contracts as PortfolioData bindings."""

    def test_volatility_same_contract(self):
        assert PORTFOLIO_VOLATILITY_LIVE_BINDING.contract is PORTFOLIO_VOLATILITY_BINDING.contract

    def test_volatility_contract_name(self):
        assert PORTFOLIO_VOLATILITY_LIVE_BINDING.contract.name == "portfolio_volatility"

    def test_variance_contract_name(self):
        assert PORTFOLIO_VARIANCE_LIVE_BINDING.contract.name == "portfolio_variance"

    def test_semivariance_contract_name(self):
        assert PORTFOLIO_SEMIVARIANCE_LIVE_BINDING.contract.name == "portfolio_semivariance"

    def test_downside_deviation_contract_name(self):
        assert PORTFOLIO_DOWNSIDE_DEVIATION_LIVE_BINDING.contract.name == "portfolio_downside_deviation"

    def test_drawdown_contract_name(self):
        assert PORTFOLIO_DRAWDOWN_LIVE_BINDING.contract.name == "portfolio_drawdown"

    def test_maximum_drawdown_contract_name(self):
        assert PORTFOLIO_MAXIMUM_DRAWDOWN_LIVE_BINDING.contract.name == "portfolio_maximum_drawdown"

    def test_var_contract_name(self):
        assert PORTFOLIO_VALUE_AT_RISK_LIVE_BINDING.contract.name == "portfolio_value_at_risk"

    def test_cvar_contract_name(self):
        assert PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING.contract.name == "portfolio_conditional_value_at_risk"

    def test_beta_contract_name(self):
        assert PORTFOLIO_BETA_LIVE_BINDING.contract.name == "portfolio_beta"

    def test_marginal_risk_contract_name(self):
        assert PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_LIVE_BINDING.contract.name == "portfolio_marginal_contribution_to_risk"

    def test_component_risk_contract_name(self):
        assert PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_LIVE_BINDING.contract.name == "portfolio_component_contribution_to_risk"


class TestPortfolioLiveBindingExecution:
    """Live bindings produce correct results using a mock registry."""

    def setup_method(self):
        self.portfolio_data = make_portfolio_data()
        self.portfolio = self.portfolio_data.portfolio
        self.registry = _make_portfolio_registry(self.portfolio_data)

    def test_volatility_matches_portfolio_data_binding(self):
        live = PORTFOLIO_VOLATILITY_LIVE_BINDING.execute(self.portfolio, self.registry)
        hist = PORTFOLIO_VOLATILITY_BINDING.execute(self.portfolio_data)
        assert abs(live - hist) < 1e-10

    def test_variance_matches_portfolio_data_binding(self):
        live = PORTFOLIO_VARIANCE_LIVE_BINDING.execute(self.portfolio, self.registry)
        hist = PORTFOLIO_VARIANCE_BINDING.execute(self.portfolio_data)
        assert abs(live - hist) < 1e-10

    def test_semivariance_returns_float(self):
        result = PORTFOLIO_SEMIVARIANCE_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, float)
        assert result >= 0

    def test_downside_deviation_returns_float(self):
        result = PORTFOLIO_DOWNSIDE_DEVIATION_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, float)
        assert result >= 0

    def test_drawdown_returns_array(self):
        result = PORTFOLIO_DRAWDOWN_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, np.ndarray)
        assert (result <= 0).all()

    def test_maximum_drawdown_returns_float(self):
        result = PORTFOLIO_MAXIMUM_DRAWDOWN_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, float)
        assert result <= 0

    def test_maximum_drawdown_matches_portfolio_data_binding(self):
        live = PORTFOLIO_MAXIMUM_DRAWDOWN_LIVE_BINDING.execute(self.portfolio, self.registry)
        hist = PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING.execute(self.portfolio_data)
        assert abs(live - hist) < 1e-10

    def test_var_returns_float(self):
        result = PORTFOLIO_VALUE_AT_RISK_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, float)

    def test_cvar_returns_float(self):
        result = PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, float)

    def test_beta_with_price_history(self):
        result = PORTFOLIO_BETA_LIVE_BINDING.execute(
            self.portfolio, self.registry, BENCHMARK_HISTORY
        )
        assert isinstance(result, float)

    def test_marginal_risk_returns_array(self):
        result = PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.portfolio_data.n_assets,)

    def test_component_risk_returns_array(self):
        result = PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_LIVE_BINDING.execute(self.portfolio, self.registry)
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.portfolio_data.n_assets,)
