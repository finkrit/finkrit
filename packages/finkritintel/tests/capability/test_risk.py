# finkritintel/tests/capability/test_risk.py
"""
Tests for RISK_CAPABILITY.
"""
from __future__ import annotations

from finkritintel.capability.base import Capability
from finkritintel.capability.risk import RISK_CAPABILITY
from finkritintel.tool.binding import ToolBinding


class TestRiskCapability:

    def test_is_capability(self):
        assert isinstance(RISK_CAPABILITY, Capability)

    def test_name(self):
        assert RISK_CAPABILITY.name == "risk_analysis"

    def test_description_not_empty(self):
        assert RISK_CAPABILITY.description

    def test_holds_tool_bindings(self):
        assert len(RISK_CAPABILITY.tools) == 20
        assert all(isinstance(tool, ToolBinding) for tool in RISK_CAPABILITY.tools)

    def test_covers_both_portfolio_and_asset_tags(self):
        tags = {tag for tool in RISK_CAPABILITY.tools for tag in tool.contract.tags}
        assert "portfolio" in tags
        assert "asset" in tags

    def test_no_duplicate_contract_names(self):
        names = [tool.contract.name for tool in RISK_CAPABILITY.tools]
        assert len(names) == len(set(names))
