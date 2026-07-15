# finkrit/tests/packages/finkritintel/tool/test_contract.py
"""
Tests for ToolContract — the intelligence-facing abstraction.
"""
from __future__ import annotations

import pytest

from finkritintel.tool.contract import ToolContract


class TestToolContract:

    def test_construction(self):
        contract = ToolContract(
            name="my_tool",
            description="Does something useful.",
        )
        assert contract.name == "my_tool"
        assert contract.description == "Does something useful."
        assert contract.summary is None

    def test_optional_summary(self):
        contract = ToolContract(
            name="my_tool",
            description="Full description.",
            summary="One liner.",
        )
        assert contract.summary == "One liner."

    def test_immutable(self):
        contract = ToolContract(name="t", description="d")
        with pytest.raises((AttributeError, TypeError)):
            contract.name = "changed"  # type: ignore[misc]

    def test_equality(self):
        a = ToolContract(name="t", description="d")
        b = ToolContract(name="t", description="d")
        assert a == b

    def test_inequality_on_name(self):
        a = ToolContract(name="tool_a", description="d")
        b = ToolContract(name="tool_b", description="d")
        assert a != b

    def test_hashable(self):
        contract = ToolContract(name="t", description="d")
        assert isinstance(hash(contract), int)
        # Can be used as a dict key
        registry: dict[ToolContract, str] = {contract: "impl"}
        assert registry[contract] == "impl"
