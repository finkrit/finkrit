# finkritintel/tests/integration/test_portfolio.py
"""
Integration tests for finkritintel.integration.finq.portfolio.

Verifies that each ToolBinding:
  - has the correct contract wired
  - executes against real finkritq functions and returns the expected type
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritintel.integration.finq.portfolio import (
    PORTFOLIO_BETA_BINDING,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING,
    PORTFOLIO_DOWNSIDE_DEVIATION_BINDING,
    PORTFOLIO_DRAWDOWN_BINDING,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING,
    PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING,
    PORTFOLIO_SEMIVARIANCE_BINDING,
    PORTFOLIO_VALUE_AT_RISK_BINDING,
    PORTFOLIO_VARIANCE_BINDING,
    PORTFOLIO_VOLATILITY_BINDING,
)
from finkritintel.tool.binding import ToolBinding

from .fixtures import BENCHMARK_HISTORY, make_portfolio_data


class TestPortfolioBindingContracts:
    """Each binding references the correct contract name."""

    def test_volatility_contract(self):
        assert PORTFOLIO_VOLATILITY_BINDING.contract.name == "portfolio_volatility"

    def test_variance_contract(self):
        assert PORTFOLIO_VARIANCE_BINDING.contract.name == "portfolio_variance"

    def test_semivariance_contract(self):
        assert PORTFOLIO_SEMIVARIANCE_BINDING.contract.name == "portfolio_semivariance"

    def test_downside_deviation_contract(self):
        assert PORTFOLIO_DOWNSIDE_DEVIATION_BINDING.contract.name == "portfolio_downside_deviation"

    def test_drawdown_contract(self):
        assert PORTFOLIO_DRAWDOWN_BINDING.contract.name == "portfolio_drawdown"

    def test_maximum_drawdown_contract(self):
        assert PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING.contract.name == "portfolio_maximum_drawdown"

    def test_value_at_risk_contract(self):
        assert PORTFOLIO_VALUE_AT_RISK_BINDING.contract.name == "portfolio_value_at_risk"

    def test_conditional_value_at_risk_contract(self):
        assert PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING.contract.name == "portfolio_conditional_value_at_risk"

    def test_beta_contract(self):
        assert PORTFOLIO_BETA_BINDING.contract.name == "portfolio_beta"

    def test_marginal_risk_contract(self):
        assert PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING.contract.name == "portfolio_marginal_contribution_to_risk"

    def test_component_risk_contract(self):
        assert PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING.contract.name == "portfolio_component_contribution_to_risk"


class TestPortfolioBindingTypes:
    """All bindings are ToolBinding instances."""

    def test_all_are_tool_bindings(self):
        bindings = [
            PORTFOLIO_VOLATILITY_BINDING,
            PORTFOLIO_VARIANCE_BINDING,
            PORTFOLIO_SEMIVARIANCE_BINDING,
            PORTFOLIO_DOWNSIDE_DEVIATION_BINDING,
            PORTFOLIO_DRAWDOWN_BINDING,
            PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING,
            PORTFOLIO_VALUE_AT_RISK_BINDING,
            PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING,
            PORTFOLIO_BETA_BINDING,
            PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING,
            PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING,
        ]
        for b in bindings:
            assert isinstance(b, ToolBinding)


class TestPortfolioBindingExecution:
    """Each binding executes and returns the correct output type."""

    def setup_method(self):
        self.portfolio_data = make_portfolio_data()

    def test_volatility_returns_float(self):
        result = PORTFOLIO_VOLATILITY_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)
        assert result > 0

    def test_variance_returns_float(self):
        result = PORTFOLIO_VARIANCE_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)
        assert result > 0

    def test_semivariance_returns_float(self):
        result = PORTFOLIO_SEMIVARIANCE_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)
        assert result >= 0

    def test_downside_deviation_returns_float(self):
        result = PORTFOLIO_DOWNSIDE_DEVIATION_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)
        assert result >= 0

    def test_drawdown_returns_array(self):
        result = PORTFOLIO_DRAWDOWN_BINDING.execute(self.portfolio_data)
        assert isinstance(result, np.ndarray)
        assert (result <= 0).all()

    def test_maximum_drawdown_returns_float(self):
        result = PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)
        assert result <= 0

    def test_value_at_risk_returns_float(self):
        result = PORTFOLIO_VALUE_AT_RISK_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)

    def test_conditional_value_at_risk_returns_float(self):
        result = PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(self.portfolio_data)
        assert isinstance(result, float)

    def test_beta_returns_float(self):
        result = PORTFOLIO_BETA_BINDING.execute(self.portfolio_data, BENCHMARK_HISTORY)
        assert isinstance(result, float)

    def test_marginal_risk_returns_array(self):
        result = PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING.execute(self.portfolio_data)
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.portfolio_data.n_assets,)

    def test_component_risk_returns_array(self):
        result = PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING.execute(self.portfolio_data)
        assert isinstance(result, np.ndarray)
        assert result.shape == (self.portfolio_data.n_assets,)

    def test_volatility_vs_variance_consistent(self):
        vol = PORTFOLIO_VOLATILITY_BINDING.execute(self.portfolio_data)
        var = PORTFOLIO_VARIANCE_BINDING.execute(self.portfolio_data)
        assert abs(vol**2 - var) < 1e-6

    def test_downside_deviation_vs_semivariance_consistent(self):
        dd = PORTFOLIO_DOWNSIDE_DEVIATION_BINDING.execute(self.portfolio_data)
        sv = PORTFOLIO_SEMIVARIANCE_BINDING.execute(self.portfolio_data)
        assert abs(dd**2 - sv) < 1e-6

    def test_cvar_gte_var(self):
        var = PORTFOLIO_VALUE_AT_RISK_BINDING.execute(self.portfolio_data)
        cvar = PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(self.portfolio_data)
        assert cvar >= var - 1e-9

    def test_component_risk_sums_to_volatility(self):
        vol = PORTFOLIO_VOLATILITY_BINDING.execute(self.portfolio_data)
        cctr = PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING.execute(self.portfolio_data)
        assert abs(cctr.sum() - vol) < 1e-6

