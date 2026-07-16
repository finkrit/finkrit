# finkritintel/tests/integration/test_asset_live.py
"""
Integration tests for finkritintel.integration.finq.asset_live.
Uses a mock DataRegistry — no network calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from finkritintel.integration.finkritq.asset_live import (
    ASSET_BETA_LIVE_BINDING,
    ASSET_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING,
    ASSET_DOWNSIDE_DEVIATION_LIVE_BINDING,
    ASSET_DRAWDOWN_LIVE_BINDING,
    ASSET_MAXIMUM_DRAWDOWN_LIVE_BINDING,
    ASSET_SEMIVARIANCE_LIVE_BINDING,
    ASSET_VALUE_AT_RISK_LIVE_BINDING,
    ASSET_VARIANCE_LIVE_BINDING,
    ASSET_VOLATILITY_LIVE_BINDING,
)
from finkritintel.integration.finkritq.asset import ASSET_VOLATILITY_BINDING

from .fixtures import BENCHMARK_HISTORY, make_portfolio_data


def _make_asset_registry(history):
    registry = MagicMock()
    registry.history.return_value = history
    return registry


class TestAssetLiveBindingContracts:
    """Live bindings reference the same contracts as PriceHistory bindings."""

    def test_volatility_same_contract(self):
        assert ASSET_VOLATILITY_LIVE_BINDING.contract is ASSET_VOLATILITY_BINDING.contract

    def test_volatility_contract_name(self):
        assert ASSET_VOLATILITY_LIVE_BINDING.contract.name == "asset_volatility"

    def test_variance_contract_name(self):
        assert ASSET_VARIANCE_LIVE_BINDING.contract.name == "asset_variance"

    def test_semivariance_contract_name(self):
        assert ASSET_SEMIVARIANCE_LIVE_BINDING.contract.name == "asset_semivariance"

    def test_downside_deviation_contract_name(self):
        assert ASSET_DOWNSIDE_DEVIATION_LIVE_BINDING.contract.name == "asset_downside_deviation"

    def test_drawdown_contract_name(self):
        assert ASSET_DRAWDOWN_LIVE_BINDING.contract.name == "asset_drawdown"

    def test_maximum_drawdown_contract_name(self):
        assert ASSET_MAXIMUM_DRAWDOWN_LIVE_BINDING.contract.name == "asset_maximum_drawdown"

    def test_var_contract_name(self):
        assert ASSET_VALUE_AT_RISK_LIVE_BINDING.contract.name == "asset_value_at_risk"

    def test_cvar_contract_name(self):
        assert ASSET_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING.contract.name == "asset_conditional_value_at_risk"

    def test_beta_contract_name(self):
        assert ASSET_BETA_LIVE_BINDING.contract.name == "asset_beta"


class TestAssetLiveBindingExecution:
    """Live bindings produce correct results using a mock registry."""

    def setup_method(self):
        portfolio_data = make_portfolio_data()
        self.asset = portfolio_data.assets[0]
        self.history = portfolio_data[self.asset]
        self.registry = _make_asset_registry(self.history)

    def test_volatility_matches_history_binding(self):
        live = ASSET_VOLATILITY_LIVE_BINDING.execute(self.asset, self.registry)
        hist = ASSET_VOLATILITY_BINDING.execute(self.history)
        assert abs(live - hist) < 1e-10

    def test_variance_returns_float(self):
        result = ASSET_VARIANCE_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)
        assert result > 0

    def test_semivariance_returns_float(self):
        result = ASSET_SEMIVARIANCE_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)
        assert result >= 0

    def test_downside_deviation_returns_float(self):
        result = ASSET_DOWNSIDE_DEVIATION_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)
        assert result >= 0

    def test_drawdown_returns_array(self):
        result = ASSET_DRAWDOWN_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, np.ndarray)
        assert (result <= 0).all()

    def test_maximum_drawdown_returns_float(self):
        result = ASSET_MAXIMUM_DRAWDOWN_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)
        assert result <= 0

    def test_var_returns_float(self):
        result = ASSET_VALUE_AT_RISK_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)

    def test_cvar_returns_float(self):
        result = ASSET_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING.execute(self.asset, self.registry)
        assert isinstance(result, float)

    def test_beta_returns_float(self):
        bench_asset = MagicMock()
        registry = MagicMock()
        registry.history.side_effect = lambda target, **_: (
            self.history if target is self.asset else BENCHMARK_HISTORY
        )
        result = ASSET_BETA_LIVE_BINDING.execute(self.asset, bench_asset, registry)
        assert isinstance(result, float)
