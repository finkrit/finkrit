# finkritintel/capability/__init__.py
"""
finkritintel.capability — capabilities: named groups of tool bindings an agent
exposes as a single unit.

  - ``base`` — the ``Capability`` type (name, description, tuple of
    ``ToolBinding``s).
  - ``risk`` — ``RISK_CAPABILITY``, the risk-analysis capability assembled from
    the finkritq integration bindings (portfolio + asset risk metrics).

Capabilities are modeled by *domain* (risk), not by object type — a single risk
capability answers both portfolio- and asset-level questions, dispatched via
``ToolContract.tags`` rather than separate capabilities.
"""

from finkritintel.capability.base import Capability
from finkritintel.capability.risk import RISK_CAPABILITY

__all__ = ["Capability", "RISK_CAPABILITY"]
