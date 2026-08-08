# finkritintel/capability/risk.py
"""
What the risk specialist can do, as two tools rather than twenty.

The per metric bindings still exist in this package and still run. They serve
the deterministic report composer through their pre-fetched twins, and they are
the implementation these two call. What changed is that they are no longer
doors a model opens directly.

Twenty was nine metrics times two scopes plus the two portfolio only
contribution metrics: twenty near identical descriptions carrying eleven ideas.
Worse, every asset tool took a single ticker, so "the betas of my holdings" was
one call per holding against a ceiling of twelve, and the model has no way to
learn the tickers in the first place (it holds an opaque portfolio id). These
two take lists and resolve holdings in code.
"""

from finkritintel.capability.base import Capability
from finkritintel.integration.finkritq import (
    ASSET_RISK_LIVE_BINDING,
    PORTFOLIO_RISK_LIVE_BINDING,
)


RISK_CAPABILITY = Capability(
    name="risk_analysis",
    description="Analyze risk for a portfolio or its individual holdings.",
    tools=(
        PORTFOLIO_RISK_LIVE_BINDING,
        ASSET_RISK_LIVE_BINDING,
    ),
)
