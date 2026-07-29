# finkritintel/capability/optimization.py

from finkritintel.capability.base import Capability
from finkritintel.integration.finkritq import (
    OPTIMIZE_MAXIMUM_SHARPE_LIVE_BINDING,
    OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING,
    PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING,
    PORTFOLIO_TAX_AWARE_REBALANCE_LIVE_BINDING,
)


# One capability is one domain, so an optimization agent stays an allocation
# specialist. Kept separate from RISK_CAPABILITY and PERFORMANCE_CAPABILITY, a
# mixed question fans out over agents at call time. The tax-aware rebalance is
# the promised composition landing here: the optimizer's target realized under
# a capital gains budget. It proposes a plan and never trades, like the rest.
# The Policy-driven variant waits on a policy surface above this layer.
OPTIMIZATION_CAPABILITY = Capability(
    name="optimization_analysis",
    description=(
        "Compute optimal portfolio allocations (minimum-variance, maximum-Sharpe) "
        "and propose tax-aware rebalancing plans toward them under a capital "
        "gains budget."
    ),
    tools=(
        OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING,
        OPTIMIZE_MAXIMUM_SHARPE_LIVE_BINDING,
        PORTFOLIO_TAX_AWARE_REBALANCE_LIVE_BINDING,
        PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING,
    ),
)
