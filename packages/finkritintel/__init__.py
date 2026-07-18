# finkritintel/__init__.py
"""
finkritintel — the bridge layer between finkritq (deterministic quant core) and
an agent framework (finagent / pydantic-ai).

It owns the *contracts* an agent needs, decoupled from both the raw finkritq
functions below and the LLM framework above:

  - ``ToolContract`` — agent-facing metadata (name, description, category, tags)
    describing *what* a tool is, independent of how it's implemented.
  - ``ToolBinding`` — pairs a contract with an input/output schema and a concrete
    implementation; ``.execute(...)`` runs it.
  - ``Capability`` — a named group of bindings (e.g. risk analysis) an agent
    exposes as one unit. Modeled by *domain*, not by object type; asset-vs-
    portfolio dispatch is via ``ToolContract.tags``.

The ``integration`` subpackage holds the adapters that wire finkritq functions
into bindings (``integration/finkritq/``), with room for other data sources
(e.g. Bloomberg) later. This layer is deliberately pydantic-free and agent-
framework-agnostic, so it survives a framework swap and is independently
publishable.
"""

from finkritintel.capability.base import Capability
from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.contract import ToolContract

__all__ = ["ToolContract", "ToolBinding", "Capability"]
