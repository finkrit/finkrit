# finkritintel/tests/capability/test_optimization.py
"""
Tests for OPTIMIZATION_CAPABILITY.
"""
from __future__ import annotations

from finkritintel.capability.base import Capability
from finkritintel.capability.optimization import OPTIMIZATION_CAPABILITY
from finkritintel.capability.performance import PERFORMANCE_CAPABILITY
from finkritintel.capability.risk import RISK_CAPABILITY
from finkritintel.tool.binding import ToolBinding


class TestOptimizationCapability:

    def test_is_capability(self):
        assert isinstance(OPTIMIZATION_CAPABILITY, Capability)

    def test_name(self):
        assert OPTIMIZATION_CAPABILITY.name == "optimization_analysis"

    def test_description_not_empty(self):
        assert OPTIMIZATION_CAPABILITY.description

    def test_holds_tool_bindings(self):
        assert len(OPTIMIZATION_CAPABILITY.tools) == 2
        assert all(isinstance(tool, ToolBinding) for tool in OPTIMIZATION_CAPABILITY.tools)

    def test_expected_tool_names(self):
        names = {tool.contract.name for tool in OPTIMIZATION_CAPABILITY.tools}
        assert names == {"optimize_minimum_variance", "optimize_maximum_sharpe"}

    def test_no_duplicate_contract_names(self):
        names = [tool.contract.name for tool in OPTIMIZATION_CAPABILITY.tools]
        assert len(names) == len(set(names))

    def test_disjoint_from_risk_and_performance(self):
        # One capability per domain: no shared tools across the three.
        opt = {tool.contract.name for tool in OPTIMIZATION_CAPABILITY.tools}
        risk = {tool.contract.name for tool in RISK_CAPABILITY.tools}
        perf = {tool.contract.name for tool in PERFORMANCE_CAPABILITY.tools}
        assert opt.isdisjoint(risk)
        assert opt.isdisjoint(perf)
