# finkritintel/capability/performance.py

from finkritintel.capability.base import Capability
from finkritintel.integration.finkritq import (
    PORTFOLIO_TOTAL_RETURN_LIVE_BINDING,
    PORTFOLIO_ANNUALIZED_RETURN_LIVE_BINDING,
    PORTFOLIO_SHARPE_RATIO_LIVE_BINDING,
    PORTFOLIO_SORTINO_RATIO_LIVE_BINDING,
    PORTFOLIO_CALMAR_RATIO_LIVE_BINDING,
)


# Kept deliberately separate from RISK_CAPABILITY. One capability is one domain,
# so a performance agent stays a pure performance specialist. Answering a mixed
# question (risk and performance together) is a fan-out over the two agents at
# call time, not a fatter capability. Benchmark-relative performance (Treynor,
# information ratio, Jensen's alpha) lands here later.
PERFORMANCE_CAPABILITY = Capability(
    name="performance_analysis",
    description="Analyze return and risk-adjusted performance for a portfolio.",
    tools=(
        PORTFOLIO_TOTAL_RETURN_LIVE_BINDING,
        PORTFOLIO_ANNUALIZED_RETURN_LIVE_BINDING,
        PORTFOLIO_SHARPE_RATIO_LIVE_BINDING,
        PORTFOLIO_SORTINO_RATIO_LIVE_BINDING,
        PORTFOLIO_CALMAR_RATIO_LIVE_BINDING,
    ),
)
