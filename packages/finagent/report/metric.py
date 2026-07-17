# finagent/report/metric.py

from __future__ import annotations

from enum import Enum


class RiskMetric(Enum):
    VOLATILITY = "volatility"
    VARIANCE = "variance"
    SEMIVARIANCE = "semivariance"
    DOWNSIDE_DEVIATION = "downside_deviation"
    VALUE_AT_RISK = "value_at_risk"
    CONDITIONAL_VALUE_AT_RISK = "conditional_value_at_risk"
    BETA = "beta"
    MAX_DRAWDOWN = "max_drawdown"
    DRAWDOWN = "drawdown"
    MARGINAL_CONTRIBUTION = "marginal_contribution"
    COMPONENT_CONTRIBUTION = "component_contribution"


# What a PM glances at first. Cheap-ish, no per-asset breakdowns. Will evolve with feedback
CORE: frozenset[RiskMetric] = frozenset(
    {
        RiskMetric.VOLATILITY,
        RiskMetric.VALUE_AT_RISK,
        RiskMetric.BETA,
        RiskMetric.MAX_DRAWDOWN,
    }
)

ALL: frozenset[RiskMetric] = frozenset(RiskMetric)

# Per-asset breakdowns only make sense for a portfolio.
_PORTFOLIO_ONLY: frozenset[RiskMetric] = frozenset(
    {RiskMetric.MARGINAL_CONTRIBUTION, RiskMetric.COMPONENT_CONTRIBUTION}
)


def resolve_metrics(metrics: frozenset[RiskMetric] | set[RiskMetric] | str) -> frozenset[RiskMetric]:
    """Accept the string aliases 'core'/'all' or an explicit metric set."""
    if isinstance(metrics, str):
        key = metrics.lower()
        if key == "core":
            return CORE
        if key == "all":
            return ALL
        raise ValueError(f"Unknown metric selector '{metrics}'. Use 'core', 'all', or a set of RiskMetric.")
    return frozenset(metrics)


def asset_metrics(metrics: frozenset[RiskMetric]) -> frozenset[RiskMetric]:
    """Drop portfolio-only metrics when reporting on a single asset."""
    return metrics - _PORTFOLIO_ONLY

