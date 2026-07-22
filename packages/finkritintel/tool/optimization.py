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
        "The minimum-variance (lowest-risk) allocation, the long-only weights that "
        "minimize portfolio volatility on a shrunk covariance, ignoring expected "
        "return. Use when the goal is the least-risky mix. Returns a weight per ticker "
        "summing to 1, a proposed target, not a trade."
    ),
    category="optimization",
    tags=("portfolio", "allocation"),
)

OPTIMIZE_MAXIMUM_SHARPE = ToolContract(
    name="optimize_maximum_sharpe",
    description=(
        "The maximum-Sharpe (best risk-adjusted) allocation, the long-only weights that "
        "maximize excess return per unit of volatility on a shrunk covariance. Use when "
        "the goal is the best return for the risk. Returns a weight per ticker summing "
        "to 1, a proposed target, not a trade."
    ),
    category="optimization",
    tags=("portfolio", "allocation"),
)
