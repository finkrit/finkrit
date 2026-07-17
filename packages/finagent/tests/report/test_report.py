# finagent/tests/report/test_report.py
"""
Direct tests for the report dataclasses -- previously only exercised
indirectly through the composer. These check the type contract itself:
defaults, immutability, kw-only construction, and independent per-instance
mutable defaults (errors dict).
"""
from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from finagent.report.report import (
    AssetRiskReport,
    BaseRiskReport,
    DrawdownSummary,
    PortfolioRiskReport,
    RiskParameters,
)


class TestDrawdownSummary:

    def test_construction(self):
        d = DrawdownSummary(max_drawdown=-0.2, current_drawdown=-0.05, periods=30)
        assert d.max_drawdown == -0.2
        assert d.current_drawdown == -0.05
        assert d.periods == 30

    def test_frozen(self):
        d = DrawdownSummary(max_drawdown=-0.2, current_drawdown=-0.05, periods=30)
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.periods = 99  # type: ignore[misc]


class TestRiskParameters:

    def test_requires_as_of(self):
        with pytest.raises(TypeError):
            RiskParameters()  # type: ignore[call-arg]

    def test_defaults(self):
        p = RiskParameters(as_of=date(2024, 1, 1))
        assert p.lookback_start is None
        assert p.lookback_end is None
        assert p.interval == "1d"
        assert p.confidence == 0.95
        assert p.annualized is True
        assert p.periods_per_year == 252
        assert p.benchmark_ticker is None

    def test_kw_only_rejects_positional(self):
        with pytest.raises(TypeError):
            RiskParameters(date(2024, 1, 1))  # type: ignore[misc]

    def test_frozen(self):
        p = RiskParameters(as_of=date(2024, 1, 1))
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.confidence = 0.99  # type: ignore[misc]


class TestBaseRiskReport:

    def _params(self) -> RiskParameters:
        return RiskParameters(as_of=date(2024, 1, 1))

    def test_all_metric_fields_default_none(self):
        r = BaseRiskReport(params=self._params())
        for field_name in (
            "volatility", "variance", "semivariance", "downside_deviation",
            "value_at_risk", "conditional_value_at_risk", "beta",
            "max_drawdown", "drawdown",
        ):
            assert getattr(r, field_name) is None, field_name

    def test_errors_defaults_to_empty_dict(self):
        r = BaseRiskReport(params=self._params())
        assert r.errors == {}

    def test_errors_default_is_independent_per_instance(self):
        # field(default_factory=dict) must give each instance its own dict --
        # a shared mutable default would leak errors across reports.
        r1 = BaseRiskReport(params=self._params())
        r2 = BaseRiskReport(params=self._params())
        r1.errors["beta"] = "no benchmark"
        assert r2.errors == {}
        assert r1.errors is not r2.errors

    def test_frozen(self):
        r = BaseRiskReport(params=self._params())
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.volatility = 0.1  # type: ignore[misc]

    def test_kw_only_rejects_positional(self):
        with pytest.raises(TypeError):
            BaseRiskReport(self._params())  # type: ignore[misc]

    def test_selective_fill_leaves_rest_none(self):
        r = BaseRiskReport(params=self._params(), max_drawdown=-0.1)
        assert r.max_drawdown == -0.1
        assert r.volatility is None
        assert r.beta is None


class TestPortfolioRiskReport:

    def _params(self) -> RiskParameters:
        return RiskParameters(as_of=date(2024, 1, 1))

    def test_requires_portfolio_id(self):
        with pytest.raises(TypeError):
            PortfolioRiskReport(params=self._params())  # type: ignore[call-arg]

    def test_inherits_base_fields(self):
        r = PortfolioRiskReport(portfolio_id="port-1", params=self._params(), volatility=0.2)
        assert r.portfolio_id == "port-1"
        assert r.volatility == 0.2
        assert r.beta is None  # inherited default

    def test_contribution_fields_default_none(self):
        r = PortfolioRiskReport(portfolio_id="port-1", params=self._params())
        assert r.marginal_contributions is None
        assert r.component_contributions is None

    def test_is_a_base_risk_report(self):
        r = PortfolioRiskReport(portfolio_id="port-1", params=self._params())
        assert isinstance(r, BaseRiskReport)


class TestAssetRiskReport:

    def _params(self) -> RiskParameters:
        return RiskParameters(as_of=date(2024, 1, 1))

    def test_requires_ticker(self):
        with pytest.raises(TypeError):
            AssetRiskReport(params=self._params())  # type: ignore[call-arg]

    def test_inherits_base_fields(self):
        r = AssetRiskReport(ticker="AAPL", params=self._params(), beta=1.1)
        assert r.ticker == "AAPL"
        assert r.beta == 1.1
        assert r.volatility is None  # inherited default

    def test_has_no_portfolio_only_fields(self):
        r = AssetRiskReport(ticker="AAPL", params=self._params())
        assert not hasattr(r, "marginal_contributions")
        assert not hasattr(r, "portfolio_id")
