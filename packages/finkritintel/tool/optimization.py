# finkritintel/tool/optimization.py
"""
Tool contracts for portfolio OPTIMIZATION (finkritq.optimize).

The self-contained optimizers: given a portfolio's own history they return an
optimal weight vector, no target model or price inputs required. Rebalancing,
tax, and policy operations need a target or a price map an LLM cannot supply as a
flat argument, so they are not exposed here yet.
"""

from finkritintel.tool.contract import ToolContract


OPTIMIZE_MINIMUM_VARIANCE = ToolContract(
    name="optimize_minimum_variance",
    description=(
        "Compute the minimum-variance (lowest-risk) portfolio weights for the "
        "holdings, long-only by default, on a shrunk covariance. Returns a weight "
        "per ticker that sums to 1."
    ),
    category="optimization",
    tags=("portfolio", "allocation"),
)

OPTIMIZE_MAXIMUM_SHARPE = ToolContract(
    name="optimize_maximum_sharpe",
    description=(
        "Compute the maximum-Sharpe (best risk-adjusted) portfolio weights for "
        "the holdings, long-only by default, on a shrunk covariance. Returns a "
        "weight per ticker that sums to 1."
    ),
    category="optimization",
    tags=("portfolio", "allocation"),
)
