# finkritintel/capability/optimization.py

from finkritintel.capability.base import Capability
from finkritintel.integration.finkritq import (
    OPTIMIZE_MAXIMUM_SHARPE_LIVE_BINDING,
    OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING,
)


# One capability is one domain, so an optimization agent stays a pure allocation
# specialist. Kept separate from RISK_CAPABILITY and PERFORMANCE_CAPABILITY, a
# mixed question fans out over agents at call time. Rebalancing, tax, and
# policy-aware operations land here once their richer inputs (a target, prices,
# a policy) have an agent-friendly surface.
OPTIMIZATION_CAPABILITY = Capability(
    name="optimization_analysis",
    description="Compute optimal portfolio allocations (minimum-variance, maximum-Sharpe).",
    tools=(
        OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING,
        OPTIMIZE_MAXIMUM_SHARPE_LIVE_BINDING,
    ),
)
