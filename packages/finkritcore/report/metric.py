# finkritcore/report/metric.py

from __future__ import annotations

# Shared names sit at the one layer everything imports, 
# exactly as LotSaleMethod does.
# Re-exported here so report callers keep a single import path.
from finkritq.datatype import RiskMetric, asset_metrics

# What stays in this module is curation. Which metrics a PM glances at first
# is a product opinion, not a math fact, and the "core"/"all" string aliases
# exist for the HTTP query param and the chat surface. Neither belongs in the
# quant core. TODO: Subject to change 

# What a PM glances at first. Cheap, no per asset breakdowns. Will evolve with feedback
CORE: frozenset[RiskMetric] = frozenset(
    {
        RiskMetric.VOLATILITY,
        RiskMetric.VALUE_AT_RISK,
        RiskMetric.BETA,
        RiskMetric.MAX_DRAWDOWN,
    }
)

ALL: frozenset[RiskMetric] = frozenset(RiskMetric)


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


__all__ = ["RiskMetric", "CORE", "ALL", "resolve_metrics", "asset_metrics"]
