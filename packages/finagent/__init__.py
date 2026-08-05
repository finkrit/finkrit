# finagent/__init__.py
"""
finagent — the agentic layer for finkrit.

It stands on two packages in parallel, not one chain. ``finkritintel`` supplies
the ``Capability`` objects it translates into tools, and ``finkritcore``
supplies the state and the deterministic services those tools run against: the
``Store`` that turns an opaque portfolio id into a ``Portfolio``, and the
report composers. finagent contains NO domain math (finkritq), NO tool
contracts (finkritintel), and NO deterministic domain services (finkritcore).
What is left is the part that needs an agent framework.

Two ways to use it, both hanging off ``Assistant``:

  - Programmatic / deterministic:  ``assistant.report("port-1")``
    Delegates to ``assistant.core``, a ``finkritcore.Desk``. No
    LLM, no API key, reproducible — the path dashboards read. A caller who
    wants only this should build the desk directly and skip finagent
    entirely, which is the reason core is a package.

  - Conversational:  ``assistant.ask("what's my drawdown?")``
    An LLM picks tools and answers in natural language.

Design bar: it must be genuinely useful the moment someone ``pip install``s it
with no database, scheduler, or tenancy. Anything needing identity-over-time
(scheduling, persistence, multi-tenant state) is not part of this package.

Sub-packages: ``agent`` (the specialists), ``adapter`` (the LLM/binding
translation machinery). See ``deps`` for the shared ``AgentDeps`` handed to
every tool via pydantic-ai's ``RunContext``, which carries core's ``Store``
plus the market data registry.

``ingest`` here is only the model fallback for a CSV. A file whose header names
the ticker, quantity, cost per share, and acquired date is mapped in code by
``finkritcore.ingest`` and never reaches a model at all;
``assistant.parse_portfolio_csv(text)`` sequences the two. Either way the
result is deliberately not auto-registered: the caller reviews and corrects it
before calling ``register_portfolio``.
"""

from finagent.agent import CapabilityAgent, RiskAgent
from finagent.assistant import Assistant
from finagent.ingest import ParsedHolding, ParsedPortfolio
from finkritcore.report import (
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
    "ParsedPortfolio",
    "ParsedHolding",
]

