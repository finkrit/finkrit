# finagent/agent/__init__.py
"""
finagent.agent — the specialists.

An agent here is a thin object wrapping exactly ONE finkritintel
``Capability``: the capability *is* the agent's toolset, so the agent is
defined by what it can do. One capability per agent, always-on — we do not use
pydantic-ai ``defer_loading`` (that only pays off when a single agent holds
many capabilities and most turns use few; a one-capability specialist always
needs its own tools).

  - ``CapabilityAgent`` (base) — wraps a capability into a pydantic-ai
    ``Agent`` and exposes the generic conversational turn in two flavours:
    ``.ask()`` (sync, for scripts/notebooks) and ``.ask_async()`` (for the web
    server / concurrent callers). Only the LLM loop is async; the risk tools it
    calls stay sync and are threadpooled by pydantic-ai. Takes its own
    ``model`` and ``instructions``, so each specialist can run a different
    (e.g. cheaper) backend than a future orchestrator.

  - ``RiskAgent`` — the risk specialist. Adds a second, deterministic surface,
    ``.report()``, which composes finkritintel bindings directly (no LLM) into
    a typed report, plus ``RISK_INSTRUCTIONS`` (the system prompt: role +
    units, deliberately short — tool schemas are auto-sent, so the prompt does
    not enumerate tools).

There is deliberately no orchestrator yet: with one specialist, delegation
would route to a single agent — a stub. When a second specialist exists (e.g.
optimization), an orchestrator delegates across them via pydantic-ai's
agent-as-tool pattern, and ``Assistant.ask`` becomes that orchestrator.
"""

from .base import CapabilityAgent
from .risk import RISK_INSTRUCTIONS, RiskAgent

__all__ = ["CapabilityAgent", "RiskAgent", "RISK_INSTRUCTIONS"]
