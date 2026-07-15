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

