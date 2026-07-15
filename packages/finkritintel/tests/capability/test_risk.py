# finkritintel/tests/capability/test_risk.py
"""
Tests for PORTFOLIO_RISK_CAPABILITY.
"""
from __future__ import annotations

from finkritintel.capability.base import Capability
from finkritintel.capability.risk import PORTFOLIO_RISK_CAPABILITY


class TestPortfolioRiskCapability:

    def test_is_capability(self):
        assert isinstance(PORTFOLIO_RISK_CAPABILITY, Capability)

    def test_name(self):
        assert PORTFOLIO_RISK_CAPABILITY.name == "risk_analysis"

    def test_description_not_empty(self):
        assert PORTFOLIO_RISK_CAPABILITY.description

    def test_starts_with_no_tools(self):
        assert PORTFOLIO_RISK_CAPABILITY.tools == ()
