# finkrit/tests/packages/finkritintel/tool/test_binding.py
"""
Tests for ToolBinding — the execution-facing abstraction.
"""
from __future__ import annotations

import pytest

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.contract import ToolContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_contract(name: str = "test_tool") -> ToolContract:
    return ToolContract(name=name, description="A test tool.", category="some tool category")


class _FakeInput:
    pass


class _FakeOutput:
    pass


class TestToolBinding:

    def test_construction(self):
        def tool_impl(x: int) -> int:
            """
            Tool implementation returns input*2
            """
            return x * 2

        binding = ToolBinding(
            contract=_make_contract(),
            input_schema=_FakeInput,
            output_schema=_FakeOutput,
            implementation=tool_impl,
        )
        assert binding.contract.name == "test_tool"
        assert binding.input_schema is _FakeInput
        assert binding.output_schema is _FakeOutput

    def test_execute_delegates_to_implementation(self):
        called_with: list = []

        def impl(*args, **kwargs):
            called_with.append((args, kwargs))
            return 42

        binding = ToolBinding(
            contract=_make_contract(),
            input_schema=_FakeInput,
            output_schema=_FakeOutput,
            implementation=impl,
        )

        result = binding.execute(1, 2, key="value")
        assert result == 42
        assert called_with == [((1, 2), {"key": "value"})]

    def test_execute_passes_kwargs(self):
        def impl(x: int, y: int = 0) -> int:
            return x + y

        binding = ToolBinding(
            contract=_make_contract(),
            input_schema=_FakeInput,
            output_schema=_FakeOutput,
            implementation=impl,
        )
        assert binding.execute(x=3, y=4) == 7

    def test_immutable(self):
        binding = ToolBinding(
            contract=_make_contract(),
            input_schema=_FakeInput,
            output_schema=_FakeOutput,
            implementation=lambda: None,
        )
        with pytest.raises((AttributeError, TypeError)):
            binding.contract = _make_contract("other")  # type: ignore[misc]

    def test_contract_accessible_for_inspection(self):
        contract = _make_contract("inspect_me")
        binding = ToolBinding(
            contract=contract,
            input_schema=_FakeInput,
            output_schema=_FakeOutput,
            implementation=lambda: None,
        )
        assert binding.contract is contract
        assert binding.contract.name == "inspect_me"

