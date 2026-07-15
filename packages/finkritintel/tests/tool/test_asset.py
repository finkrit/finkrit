# finkritintel/tests/tool/test_asset.py

from __future__ import annotations

import pytest

from finkritintel.tool.asset import (
    ASSET_BETA,
    ASSET_CONDITIONAL_VALUE_AT_RISK,
    ASSET_DOWNSIDE_DEVIATION,
    ASSET_DRAWDOWN,
    ASSET_MAXIMUM_DRAWDOWN,
    ASSET_SEMIVARIANCE,
    ASSET_VALUE_AT_RISK,
    ASSET_VARIANCE,
    ASSET_VOLATILITY,
)
from finkritintel.tool.contract import ToolContract


EXPECTED = {
    ASSET_VOLATILITY: (
        "asset_volatility",
        ("asset", "volatility"),
    ),
    ASSET_VARIANCE: (
        "asset_variance",
        ("asset", "variance"),
    ),
    ASSET_SEMIVARIANCE: (
        "asset_semivariance",
        ("asset", "downside"),
    ),
    ASSET_DOWNSIDE_DEVIATION: (
        "asset_downside_deviation",
        ("asset", "downside"),
    ),
    ASSET_DRAWDOWN: (
        "asset_drawdown",
        ("asset", "drawdown"),
    ),
    ASSET_MAXIMUM_DRAWDOWN: (
        "asset_maximum_drawdown",
        ("asset", "drawdown"),
    ),
    ASSET_VALUE_AT_RISK: (
        "asset_value_at_risk",
        ("asset", "value-at-risk"),
    ),
    ASSET_CONDITIONAL_VALUE_AT_RISK: (
        "asset_conditional_value_at_risk",
        ("asset", "value-at-risk"),
    ),
    ASSET_BETA: (
        "asset_beta",
        ("asset", "beta"),
    ),
}


ALL_CONTRACTS = tuple(EXPECTED.keys())


class TestAssetContracts:

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_is_tool_contract(self, contract):
        assert isinstance(contract, ToolContract)

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_category_is_risk(self, contract):
        assert contract.category == "risk"

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_asset_tag_present(self, contract):
        assert "asset" in contract.tags

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_name_not_empty(self, contract):
        assert contract.name

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_description_not_empty(self, contract):
        assert contract.description

    @pytest.mark.parametrize("contract", ALL_CONTRACTS)
    def test_hashable(self, contract):
        assert isinstance(hash(contract), int)

    def test_all_names_unique(self):
        names = [contract.name for contract in ALL_CONTRACTS]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize(
        ("contract", "expected_name", "expected_tags"),
        [
            (contract, name, tags)
            for contract, (name, tags)
            in EXPECTED.items()
        ],
    )
    def test_identity(
        self,
        contract,
        expected_name,
        expected_tags,
    ):
        assert contract.name == expected_name
        assert contract.tags == expected_tags
        