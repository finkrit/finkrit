# finagent/report/report.py
"""
Structured risk output. One type family serving three consumers:
deterministic .report(), LLM output_type (later), and a dashboard payload.

All metric fields are Optional -- a report is filled selectively per the
requested metric set, so "only drawdown" is a report with one field set
and the rest None. finkritq/finkritintel stay pydantic-free; these live
in finagent (plain frozen dataclasses).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from finkritq.datatype import ReturnCalculationMethod, VaREstimationMethod


@dataclass(frozen=True, slots=True, kw_only=True)
class DrawdownSummary:
    max_drawdown: float            # most negative point over the window (e.g. -0.23)
    current_drawdown: float        # drawdown as of the last observation
    periods: int
    trough_date: date | None = None  # date of the max-drawdown point (for the dashboard panel)


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskParameters:
    """Everything needed to label and reproduce the numbers on a dashboard."""

    as_of: date
    lookback_start: date | None = None
    lookback_end: date | None = None
    interval: str = "1d"
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    var_method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    annualized: bool = True
    periods_per_year: int = 252
    benchmark_ticker: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseRiskReport:
    params: RiskParameters

    volatility: float | None = None
    variance: float | None = None
    semivariance: float | None = None
    downside_deviation: float | None = None
    value_at_risk: float | None = None
    conditional_value_at_risk: float | None = None
    beta: float | None = None
    max_drawdown: float | None = None
    drawdown: DrawdownSummary | None = None

    # Metric name -> reason, for metrics that were requested but couldn't be
    # computed (e.g. no benchmark, data fetch failed). Keeps a report partial
    # rather than failing the whole thing.
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioRiskReport(BaseRiskReport):
    portfolio_id: str
    marginal_contributions: dict[str, float] | None = None
    component_contributions: dict[str, float] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetRiskReport(BaseRiskReport):
    ticker: str

