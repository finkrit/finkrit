# finkritcore/report/__init__.py
"""
finkritcore.report — structured risk output and the deterministic composer.

This is finkritcore's answer to "what does analyzing risk actually return?" One
type family serves three consumers at once: the deterministic ``.report()``
return value, a (future) LLM ``output_type`` for structured extraction, and a
dashboard payload. Kept here decoupling finkritintel from AI libs
these are plain frozen dataclasses.

Contents:

  - ``metric`` — ``RiskMetric`` enum and the ``CORE`` / ``ALL`` selector sets.
    ``CORE`` (volatility, VaR, beta, max-drawdown) is the default: what a PM
    glances at first. ``resolve_metrics`` accepts the ``"core"``/``"all"``
    string aliases or an explicit set.

  - ``report`` — the output types. Every metric field is ``Optional`` and
    defaults to ``None``, so a report is filled *selectively*: "only drawdown"
    is a report with one field set and the rest ``None``. ``RiskParameters``
    (always present) records the lookback/method/benchmark so a dashboard can
    label and reproduce the numbers. Portfolio and asset reports are distinct
    shapes (portfolio adds per-asset risk contributions).

  - ``composer`` — ``compose_portfolio_risk_report``: the deterministic path.
    Fetches ``PortfolioData`` and the benchmark ONCE, then calls the
    *pre-fetched* finkritintel bindings against that shared data (this is why
    both live and pre-fetched binding variants exist). Resilient by design: a
    metric that cannot be computed is recorded in ``report.errors`` and left
    ``None`` rather than failing the whole report — a dashboard needs partial
    success.

  - ``tax_signals`` — ``compose_tax_signals``: the actionable tax view
    (harvestable lots, wash sale warnings, long term countdowns), each signal
    priced at assumed marginal rates. Lot level on purpose: it goes from code
    straight to the owner's dashboard, never through the model.
"""

from .composer import DEFAULT_BENCHMARK, compose_portfolio_risk_report
from .metric import ALL, CORE, RiskMetric
from .report import (
    AssetRiskReport,
    BaseRiskReport,
    DrawdownSummary,
    PortfolioRiskReport,
    RiskParameters,
)
from .tax_signals import (
    CountdownSignal,
    HarvestSignal,
    TaxSignalsReport,
    compose_tax_signals,
)

__all__ = [
    "RiskMetric",
    "CORE",
    "ALL",
    "RiskParameters",
    "DrawdownSummary",
    "BaseRiskReport",
    "PortfolioRiskReport",
    "AssetRiskReport",
    "compose_portfolio_risk_report",
    "DEFAULT_BENCHMARK",
    "HarvestSignal",
    "CountdownSignal",
    "TaxSignalsReport",
    "compose_tax_signals",
]
