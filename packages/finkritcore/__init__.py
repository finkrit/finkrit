# finkritcore/__init__.py
"""
finkritcore — the deterministic domain layer.

What the client holds, and the services over it that reach an answer in code:
the ``Store`` that resolves an id to a ``Portfolio``, the report composers
behind the dashboard, the CSV mapper that reads a labelled export without
asking anyone, and the ``Desk`` tying the three to one store and one
market data registry.

Nothing here imports ``pydantic_ai`` or ``finagent``, and
``tests/test_layering.py`` fails the suite if that ever stops being true. The
promise is worth a test rather than a comment: it is what lets the whole
dashboard run with no model and no API key, and it is where the compliance
boundary sits, since client holdings are resolved here and only computed
numbers travel upward.

Sibling of ``finkritintel``, which is the other half of the answer: intel is
what the system can *compute* (tool contracts for any agent framework), core is
what the client *holds*. ``finagent`` stands on both, adding the agentic
runtime that neither of them knows about.
"""
from finkritcore.ingest import (
    CSV_ALIASES,
    CSV_DATE_FORMATS,
    DEFAULT_PORTFOLIO_NAME,
    ParsedHolding,
    ParsedPortfolio,
    parse_portfolio_csv_in_code,
)
from finkritcore.report import (
    AssetRiskReport,
    PortfolioRiskReport,
    RiskMetric,
    TaxSignalsReport,
    compose_portfolio_risk_report,
    compose_tax_signals,
)
from finkritcore.desk import Desk, default_registry
from finkritcore.store import (
    DEFAULT_PORTFOLIO_ID,
    AssetNotFoundError,
    InMemoryStore,
    PortfolioNotFoundError,
    Store,
)

__all__ = [
    "Desk",
    "default_registry",
    "Store",
    "InMemoryStore",
    "PortfolioNotFoundError",
    "AssetNotFoundError",
    "DEFAULT_PORTFOLIO_ID",
    "ParsedPortfolio",
    "ParsedHolding",
    "parse_portfolio_csv_in_code",
    "DEFAULT_PORTFOLIO_NAME",
    "CSV_ALIASES",
    "CSV_DATE_FORMATS",
    "RiskMetric",
    "PortfolioRiskReport",
    "AssetRiskReport",
    "compose_portfolio_risk_report",
    "TaxSignalsReport",
    "compose_tax_signals",
]
