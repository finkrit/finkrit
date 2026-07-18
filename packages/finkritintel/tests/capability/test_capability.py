# finkritintel/tests/capability/test_capability.py
"""
Tests for the Capability base class.
"""
from __future__ import annotations

import pytest

from finkritintel.capability.base import Capability


class TestCapability:

    def test_construction(self):
        cap = Capability(name="test", description="A test capability.")
        assert cap.name == "test"
        assert cap.description == "A test capability."

    def test_starts_with_no_tools(self):
        cap = Capability(name="test", description="d")
        assert cap.tools == ()

    def test_immutable(self):
        cap = Capability(name="test", description="d")
        with pytest.raises((AttributeError, TypeError)):
            cap.name = "changed"  # type: ignore[misc]

    # --- I-5: invariants enforced by __post_init__ ---

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError):
            Capability(name="", description="d")

    def test_rejects_empty_description(self):
        with pytest.raises(ValueError):
            Capability(name="test", description="")

    def test_rejects_duplicate_contract_names(self):
        from finkritintel.tool.binding import ToolBinding
        from finkritintel.tool.contract import ToolContract

        def _binding(name: str) -> ToolBinding:
            return ToolBinding(
                contract=ToolContract(name=name, description="d", category="risk"),
                input_schema=object,
                output_schema=object,
                implementation=lambda: None,
            )

        with pytest.raises(ValueError, match="Duplicate"):
            Capability(name="c", description="d", tools=(_binding("dup"), _binding("dup")))

