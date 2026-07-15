# finkritintel/tests/integration/test_asset.py
"""
Integration tests for finkritintel.integration.finq.asset.

Verifies that each ToolBinding:
  - has the correct contract wired
  - executes against real finkritq functions and returns the expected type
"""
from __future__ import annotations

import numpy as np

from finkritintel.integration.finq.asset import (
    ASSET_BETA_BINDING,
    ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING,
    ASSET_DOWNSIDE_DEVIATION_BINDING,
    ASSET_DRAWDOWN_BINDING,
    ASSET_MAXIMUM_DRAWDOWN_BINDING,
    ASSET_SEMIVARIANCE_BINDING,
    ASSET_VALUE_AT_RISK_BINDING,
    ASSET_VARIANCE_BINDING,
    ASSET_VOLATILITY_BINDING,
)
from finkritintel.tool.binding import ToolBinding

from .fixtures import BENCHMARK_HISTORY, make_portfolio_data


def _asset_history():
    """Single-asset PriceHistory from the two-stock portfolio fixture."""
    portfolio_data = make_portfolio_data()
    return portfolio_data[portfolio_data.assets[0]]


class TestAssetBindingContracts:
    """Each binding references the correct contract name."""

    def test_volatility_contract(self):
        assert ASSET_VOLATILITY_BINDING.contract.name == "asset_volatility"

    def test_variance_contract(self):
        assert ASSET_VARIANCE_BINDING.contract.name == "asset_variance"

    def test_semivariance_contract(self):
        assert ASSET_SEMIVARIANCE_BINDING.contract.name == "asset_semivariance"

    def test_downside_deviation_contract(self):
        assert ASSET_DOWNSIDE_DEVIATION_BINDING.contract.name == "asset_downside_deviation"

    def test_drawdown_contract(self):
        assert ASSET_DRAWDOWN_BINDING.contract.name == "asset_drawdown"

    def test_maximum_drawdown_contract(self):
        assert ASSET_MAXIMUM_DRAWDOWN_BINDING.contract.name == "asset_maximum_drawdown"

    def test_value_at_risk_contract(self):
        assert ASSET_VALUE_AT_RISK_BINDING.contract.name == "asset_value_at_risk"

    def test_conditional_value_at_risk_contract(self):
        assert ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING.contract.name == "asset_conditional_value_at_risk"

    def test_beta_contract(self):
        assert ASSET_BETA_BINDING.contract.name == "asset_beta"


class TestAssetBindingTypes:
    """All bindings are ToolBinding instances."""

    def test_all_are_tool_bindings(self):
        bindings = [
            ASSET_VOLATILITY_BINDING,
            ASSET_VARIANCE_BINDING,
            ASSET_SEMIVARIANCE_BINDING,
            ASSET_DOWNSIDE_DEVIATION_BINDING,
            ASSET_DRAWDOWN_BINDING,
            ASSET_MAXIMUM_DRAWDOWN_BINDING,
            ASSET_VALUE_AT_RISK_BINDING,
            ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING,
            ASSET_BETA_BINDING,
        ]
        for b in bindings:
            assert isinstance(b, ToolBinding)


class TestAssetBindingExecution:
    """Each binding executes and returns the correct output type."""

    def setup_method(self):
        self.history = _asset_history()

    def test_volatility_returns_float(self):
        result = ASSET_VOLATILITY_BINDING.execute(self.history)
        assert isinstance(result, float)
        assert result > 0

    def test_variance_returns_float(self):
        result = ASSET_VARIANCE_BINDING.execute(self.history)
        assert isinstance(result, float)
        assert result > 0

    def test_semivariance_returns_float(self):
        result = ASSET_SEMIVARIANCE_BINDING.execute(self.history)
        assert isinstance(result, float)
        assert result >= 0

    def test_downside_deviation_returns_float(self):
        result = ASSET_DOWNSIDE_DEVIATION_BINDING.execute(self.history)
        assert isinstance(result, float)
        assert result >= 0

    def test_drawdown_returns_array(self):
        result = ASSET_DRAWDOWN_BINDING.execute(self.history)
        assert isinstance(result, np.ndarray)
        assert (result <= 0).all()

    def test_maximum_drawdown_returns_float(self):
        result = ASSET_MAXIMUM_DRAWDOWN_BINDING.execute(self.history)
        assert isinstance(result, float)
        assert result <= 0

    def test_value_at_risk_returns_float(self):
        result = ASSET_VALUE_AT_RISK_BINDING.execute(self.history)
        assert isinstance(result, float)

    def test_conditional_value_at_risk_returns_float(self):
        result = ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(self.history)
        assert isinstance(result, float)

    def test_beta_returns_float(self):
        result = ASSET_BETA_BINDING.execute(self.history, BENCHMARK_HISTORY)
        assert isinstance(result, float)

    def test_volatility_vs_variance_consistent(self):
        vol = ASSET_VOLATILITY_BINDING.execute(self.history)
        var = ASSET_VARIANCE_BINDING.execute(self.history)
        assert abs(vol**2 - var) < 1e-6

    def test_downside_deviation_vs_semivariance_consistent(self):
        dd = ASSET_DOWNSIDE_DEVIATION_BINDING.execute(self.history)
        sv = ASSET_SEMIVARIANCE_BINDING.execute(self.history)
        assert abs(dd**2 - sv) < 1e-6

    def test_cvar_gte_var(self):
        var = ASSET_VALUE_AT_RISK_BINDING.execute(self.history)
        cvar = ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(self.history)
        assert cvar >= var - 1e-9
