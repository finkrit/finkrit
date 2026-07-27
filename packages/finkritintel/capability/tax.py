# finkritintel/capability/tax.py

from finkritintel.capability.base import Capability
from finkritintel.integration.finkritq import (
    PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING,
    PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING,
    PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING,
)


# The read-only tax lens, kept separate from the other domains like the rest.
# It describes the current tax position of a portfolio (unrealized gains, harvest
# candidates, and the long versus short term split) and never places a trade.
# Tax-aware rebalancing lands here later, once the optimizer-to-tax composition
# and a policy surface exist, see the deferred rebalancing task.
TAX_CAPABILITY = Capability(
    name="tax_analysis",
    description="Analyze the current tax position of a portfolio, gains, harvestable losses, and holding period.",
    tools=(
        PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING,
        PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING,
        PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING,
    ),
)
