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
        # Two, not twenty. Nine metrics across two scopes made twenty near
        # identical descriptions carrying eleven ideas, and every asset tool
        # took a single ticker, so a per holding question was one call each.
        # These take lists. The per metric bindings still exist and still run,
        # they are simply no longer what a model chooses between.
        assert len(RISK_CAPABILITY.tools) == 2
        assert all(isinstance(tool, ToolBinding) for tool in RISK_CAPABILITY.tools)

    def test_covers_both_portfolio_and_asset_tags(self):
        tags = {tag for tool in RISK_CAPABILITY.tools for tag in tool.contract.tags}
        assert "portfolio" in tags
        assert "asset" in tags

    def test_every_tool_takes_a_metric_list(self):
        # The property that replaces one tool per metric. Losing it would mean
        # the collapse had silently regressed to single purpose tools.
        for tool in RISK_CAPABILITY.tools:
            fields = tool.input_schema.__dataclass_fields__
            assert "metrics" in fields, tool.contract.name

    def test_the_asset_tool_takes_a_ticker_list(self):
        # And it is optional, meaning every holding. The model holds an opaque
        # portfolio id and cannot name a ticker, so this is the parameter that
        # makes "the betas of my holdings" answerable at all.
        asset_tool = next(t for t in RISK_CAPABILITY.tools if t.contract.name == "asset_risk")
        assert asset_tool.input_schema.__dataclass_fields__["assets"].default is None

    def test_no_duplicate_contract_names(self):
        names = [tool.contract.name for tool in RISK_CAPABILITY.tools]
        assert len(names) == len(set(names))
