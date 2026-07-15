# finkritintel/tests/tool/test_portfolio.py
"""
Tests for tool/portfolio.py — all portfolio ToolContract instances.
"""
from __future__ import annotations

import pytest

from finkritintel.tool.contract import ToolContract
from finkritintel.tool.portfolio import (
    PORTFOLIO_BETA,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK,
    PORTFOLIO_DOWNSIDE_DEVIATION,
    PORTFOLIO_DRAWDOWN,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK,
    PORTFOLIO_MAXIMUM_DRAWDOWN,
    PORTFOLIO_SEMIVARIANCE,
    PORTFOLIO_VALUE_AT_RISK,
    PORTFOLIO_VARIANCE,
    PORTFOLIO_VOLATILITY,
)

ALL_CONTRACTS = [
    PORTFOLIO_VOLATILITY,
    PORTFOLIO_VARIANCE,
    PORTFOLIO_SEMIVARIANCE,
    PORTFOLIO_DOWNSIDE_DEVIATION,
    PORTFOLIO_DRAWDOWN,
    PORTFOLIO_MAXIMUM_DRAWDOWN,
    PORTFOLIO_VALUE_AT_RISK,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK,
    PORTFOLIO_BETA,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK,
]


class TestPortfolioContractTypes:

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_is_tool_contract(self, contract):
        assert isinstance(contract, ToolContract)

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_category_is_risk(self, contract):
        assert contract.category == "risk"

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_portfolio_tag_present(self, contract):
        assert "portfolio" in contract.tags

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_name_not_empty(self, contract):
        assert contract.name

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_description_not_empty(self, contract):
        assert contract.description

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_hashable(self, contract):
        assert isinstance(hash(contract), int)


class TestPortfolioContractIdentity:

    def test_all_names_unique(self):
        names = [c.name for c in ALL_CONTRACTS]
        assert len(names) == len(set(names))

    def test_volatility_name(self):
        assert PORTFOLIO_VOLATILITY.name == "portfolio_volatility"

    def test_variance_name(self):
        assert PORTFOLIO_VARIANCE.name == "portfolio_variance"

    def test_semivariance_name(self):
        assert PORTFOLIO_SEMIVARIANCE.name == "portfolio_semivariance"

    def test_downside_deviation_name(self):
        assert PORTFOLIO_DOWNSIDE_DEVIATION.name == "portfolio_downside_deviation"

    def test_drawdown_name(self):
        assert PORTFOLIO_DRAWDOWN.name == "portfolio_drawdown"

    def test_maximum_drawdown_name(self):
        assert PORTFOLIO_MAXIMUM_DRAWDOWN.name == "portfolio_maximum_drawdown"

    def test_value_at_risk_name(self):
        assert PORTFOLIO_VALUE_AT_RISK.name == "portfolio_value_at_risk"

    def test_conditional_value_at_risk_name(self):
        assert PORTFOLIO_CONDITIONAL_VALUE_AT_RISK.name == "portfolio_conditional_value_at_risk"

    def test_beta_name(self):
        assert PORTFOLIO_BETA.name == "portfolio_beta"

    def test_marginal_risk_name(self):
        assert PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK.name == "portfolio_marginal_contribution_to_risk"

    def test_component_risk_name(self):
        assert PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK.name == "portfolio_component_contribution_to_risk"


class TestPortfolioContractTags:

    def test_volatility_tags(self):
        assert PORTFOLIO_VOLATILITY.tags == ("portfolio", "volatility")

    def test_variance_tags(self):
        assert PORTFOLIO_VARIANCE.tags == ("portfolio", "variance")

    def test_semivariance_tags(self):
        assert PORTFOLIO_SEMIVARIANCE.tags == ("portfolio", "downside")

    def test_downside_deviation_tags(self):
        assert PORTFOLIO_DOWNSIDE_DEVIATION.tags == ("portfolio", "downside")

    def test_drawdown_tags(self):
        assert PORTFOLIO_DRAWDOWN.tags == ("portfolio", "drawdown")

    def test_maximum_drawdown_tags(self):
        assert PORTFOLIO_MAXIMUM_DRAWDOWN.tags == ("portfolio", "drawdown")

    def test_value_at_risk_tags(self):
        assert PORTFOLIO_VALUE_AT_RISK.tags == ("portfolio", "value-at-risk")

    def test_conditional_value_at_risk_tags(self):
        assert PORTFOLIO_CONDITIONAL_VALUE_AT_RISK.tags == ("portfolio", "value-at-risk")

    def test_beta_tags(self):
        assert PORTFOLIO_BETA.tags == ("portfolio", "beta")

    def test_marginal_risk_tags(self):
        assert PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK.tags == ("portfolio", "contribution")

    def test_component_risk_tags(self):
        assert PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK.tags == ("portfolio", "contribution")

