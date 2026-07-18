# finkritintel/tests/test_public_api.py
"""I-2: the package root re-exports its public surface (an independently
publishable package's __init__ is its API declaration)."""
from __future__ import annotations

import finkritintel
from finkritintel import capability


def test_root_exports():
    assert finkritintel.ToolContract is not None
    assert finkritintel.ToolBinding is not None
    assert finkritintel.Capability is not None


def test_capability_subpackage_exports_risk():
    assert capability.RISK_CAPABILITY is not None
    assert capability.RISK_CAPABILITY.name == "risk_analysis"
