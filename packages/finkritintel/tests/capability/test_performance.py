# finkritintel/tests/capability/test_performance.py
"""
Tests for PERFORMANCE_CAPABILITY.
"""
from __future__ import annotations

from finkritintel.capability.base import Capability
from finkritintel.capability.performance import PERFORMANCE_CAPABILITY
from finkritintel.capability.risk import RISK_CAPABILITY
from finkritintel.tool.binding import ToolBinding


class TestPerformanceCapability:

    def test_is_capability(self):
        assert isinstance(PERFORMANCE_CAPABILITY, Capability)

    def test_name(self):
        assert PERFORMANCE_CAPABILITY.name == "performance_analysis"

    def test_description_not_empty(self):
        assert PERFORMANCE_CAPABILITY.description

    def test_holds_tool_bindings(self):
        assert len(PERFORMANCE_CAPABILITY.tools) == 5  # 5 portfolio performance
        assert all(isinstance(tool, ToolBinding) for tool in PERFORMANCE_CAPABILITY.tools)

    def test_expected_metric_names(self):
        names = {tool.contract.name for tool in PERFORMANCE_CAPABILITY.tools}
        assert names == {
            "portfolio_total_return",
            "portfolio_annualized_return",
            "portfolio_sharpe_ratio",
            "portfolio_sortino_ratio",
            "portfolio_calmar_ratio",
        }

    def test_no_duplicate_contract_names(self):
        names = [tool.contract.name for tool in PERFORMANCE_CAPABILITY.tools]
        assert len(names) == len(set(names))

    def test_disjoint_from_risk_capability(self):
        # One capability per domain: performance and risk must not share tools.
        perf = {tool.contract.name for tool in PERFORMANCE_CAPABILITY.tools}
        risk = {tool.contract.name for tool in RISK_CAPABILITY.tools}
        assert perf.isdisjoint(risk)
