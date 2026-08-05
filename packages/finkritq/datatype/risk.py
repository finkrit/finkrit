# finkrit/packages/finkritq/datatype/risk.py
from enum import Enum


class VaREstimationMethod(Enum):
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    PARAMETRIC = "parametric"


class WeightingBasis(Enum):
    """
    WHAT IS A "BASIS"?
    ==================
    Every portfolio risk number (volatility, VaR, drawdown, ...) is computed from
    a single time series: the portfolio's period-by-period return over the
    lookback window. But a portfolio of several assets does not have *one*
    obvious return series -- you first have to answer "as prices moved over the
    window, how did the money stay divided across the assets?" That modelling
    choice is the *basis*. It does not change the holdings or the price data; it
    changes which hypothetical portfolio the returns describe, and therefore what
    every downstream metric actually means.

    Two bases are meaningful, and they differ in what is held constant:

    ------------------------------------------------------------------------
    CONSTANT_MIX  -- hold the WEIGHTS constant
    ------------------------------------------------------------------------
    Fix today's weight vector `w` (e.g. 60% A / 40% B) and apply it to every
    period in the window:  r_p(t) = Σ_i w_i · r_i(t).

    Keeping weights fixed as prices move is only possible if you rebalance every
    period: sell the winners, buy the losers, back to `w`. So this basis models
    a *continuously rebalanced* portfolio. Because it is defined purely by `w`
    and the asset returns, its variance is exactly the quadratic form wᵀΣw (Σ =
    asset covariance matrix), which is why it is the ONLY basis in which
    covariance-space quantities are defined:
        - variance / volatility (wᵀΣw)
        - marginal / component contribution to risk (MCTR / CCTR)
    Interpretation: *ex-ante* / forward-looking -- "the risk of my target
    allocation, if I keep holding these weights."

    ------------------------------------------------------------------------
    BUY_AND_HOLD: hold the SHARE COUNTS constant
    ------------------------------------------------------------------------
    Fix today's share counts `q` (e.g. 100 shares of A, 50 of B) and let the
    portfolio value be whatever those shares are worth each day:
        V(t) = Σ_i q_i · P_i(t),   r_p(t) = V(t)/V(t-1) - 1.
    Here nobody rebalances, so the weights DRIFT: a winner becomes a larger
    fraction of the book on its own. This is the return series of the *actual
    dollar path* of the exact lots held.
    Interpretation: *realized* / backward-looking -- "what these specific lots
    actually did." It is the `honest` basis for anything path dependent
    (drawdown: you can only draw down the real value path), and it is the basis a
    Sharpe / Sortino numerator should be built on.

    ------------------------------------------------------------------------
    WHY BOTH EXIST AND WHY THE CHOICE MUST BE EXPLICIT
    ------------------------------------------------------------------------
    For a portfolio that has barely drifted the two bases nearly agree; the gap
    grows with dispersion across holdings and with the length of the window.
    They answer genuinely different questions, so mixing them silently within one
    report (e.g. constant-mix volatility next to buy-and-hold VaR) describes two
    different portfolios without saying so, this is what this enum fixes.
    A Sharpe ratio is the sharpest example: its numerator (a return) and
    denominator (a volatility) MUST come from the same basis or the ratio is
    meaningless.

    Not every metric offers a choice: MCTR/CCTR are CONSTANT_MIX-only (no
    buy-and-hold analogue exists), and drawdown is inherently BUY_AND_HOLD.
    Everything else genuinely supports either. Not every metric commits to a
    single report wide default: that choice is left to the caller.
    """

    # Value strings are stable identifiers (serialization / tool schemas); do not
    # rename without updating any persisted references.
    CONSTANT_MIX = "constant_mix"  # fixed weights  -> ex-ante / rebalanced
    BUY_AND_HOLD = "buy_and_hold"  # fixed shares   -> realized / drifting


class RiskMetric(Enum):
    """The risk metrics the stack computes, named once.

    Cross-layer vocabulary, like ``LotSaleMethod``: the report composers above
    select with these names and tool contracts carry them in their schemas,
    and those layers do not import each other, so the shared names have to
    live down here. The quant functions themselves do not take a
    ``RiskMetric``, there is one function per metric, so each member is the
    name of a function's result rather than a parameter to it.

    What does NOT live here is curation. Which metrics a dashboard shows first
    is a product opinion, and those selections stay in the layers that hold
    opinions.
    """

    # Value strings are stable identifiers (serialization / tool schemas); do
    # not rename without updating any persisted references.
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


# Contribution metrics decompose a portfolio's risk across its holdings, so
# they exist only at portfolio scope: a single asset has nothing to decompose.
# A semantic fact about the metrics, kept next to them rather than in any one
# consumer, so every layer agrees on what an asset-scope report can carry.
PORTFOLIO_ONLY_METRICS: frozenset[RiskMetric] = frozenset(
    {RiskMetric.MARGINAL_CONTRIBUTION, RiskMetric.COMPONENT_CONTRIBUTION}
)


def asset_metrics(metrics: frozenset[RiskMetric]) -> frozenset[RiskMetric]:
    """``metrics`` with the portfolio-only ones dropped, for asset scope."""
    return frozenset(metrics) - PORTFOLIO_ONLY_METRICS
