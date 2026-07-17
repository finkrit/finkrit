# finagent/__init__.py
"""
finagent — the conversational + programmatic agent layer for finkrit.

Top of the three-package chain ``finagent -> finkritintel -> finkritq`` (one
direction only). finagent contains NO domain math (that is finkritq) and NO
tool contract/schema/capability definitions (that is finkritintel). Its whole
job is to translate finkritintel ``Capability`` objects into something an LLM
can drive, and to shape the results into structured reports.

Two ways to use it, both hanging off ``Assistant``:

  - Programmatic / deterministic:  ``assistant.risk.report("port-1", deps)``
    Runs the finkritintel bindings directly and returns a typed
    ``PortfolioRiskReport``. No LLM, no API key, reproducible — the path meant
    for dashboards and non-conversational callers.

  - Conversational:  ``assistant.ask("what's my drawdown?")``
    An LLM picks tools and answers in natural language.

Design bar: it must be genuinely useful the moment someone ``pip install``s it
with no database, scheduler, or tenancy. Anything needing identity-over-time
(scheduling, persistence, multi-tenant state) is not part of this package.

Sub-packages: ``agent`` (the specialists), ``report`` (structured output +
deterministic composer), ``adapter`` (the LLM/binding translation machinery),
``store`` (id -> domain-object resolution). See ``deps`` for the shared
``AgentDeps`` handed to every tool via pydantic-ai's ``RunContext``.
"""

from finagent.agent import CapabilityAgent, RiskAgent
from finagent.assistant import Assistant
from finagent.report import (
    ALL,
    CORE,
    AssetRiskReport,
    PortfolioRiskReport,
    RiskMetric,
)

__all__ = [
    "Assistant",
    "RiskAgent",
    "CapabilityAgent",
    "RiskMetric",
    "CORE",
    "ALL",
    "PortfolioRiskReport",
    "AssetRiskReport",
]

