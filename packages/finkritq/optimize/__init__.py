# finkrit/packages/finkritq/optimize/__init__.py
"""
finkritq.optimize, portfolio optimization: turning a covariance matrix and
expected returns into weights.

A top-level analytic pillar, peer to ``anal`` (risk/performance). It consumes the
same PortfolioData and reuses ``anal.risk.covariance_matrix`` for Σ, adding an
expected-return estimator (``expected_returns``) for μ.

Today: the closed-form, budget-only (wᵀ1 = 1) mean-variance optima, global
minimum variance, tangency/max-Sharpe, and the efficient frontier, which need
only numpy. Constrained variants (long-only, weight bounds) and risk-based
allocation (risk parity) need a quadratic-program solver and land later.
"""
from finkritq.optimize.expected_returns import (
    expected_returns,
    expected_returns_from_returns,
)
from finkritq.optimize.meanvariance import (
    FrontierPoint,
    efficient_frontier,
    efficient_frontier_portfolio,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    minimum_variance_weights,
    portfolio_return_from_weights,
    portfolio_sharpe_from_weights,
    portfolio_variance_from_weights,
    portfolio_volatility_from_weights,
    tangency_weights,
    target_return_weights,
)
from finkritq.optimize.rebalance import (
    RebalanceTrade,
    rebalance_to_model,
    rebalance_to_policy,
    total_drift,
)
from finkritq.optimize.lotselection import (
    LotSaleMethod,
    RealizedLot,
    SaleResult,
    select_lots_to_sell,
)
from finkritq.optimize.harvest import (
    HarvestCandidate,
    HarvestReport,
    harvest_candidates,
)
from finkritq.optimize.cashflow import (
    CashFlowPlan,
    invest_cashflow,
)
from finkritq.optimize.taxrebalance import (
    TaxRebalancePlan,
    TaxRebalanceSell,
    tax_aware_rebalance,
    tax_aware_rebalance_to_policy,
)

__all__ = [
    # expected returns
    "expected_returns",
    "expected_returns_from_returns",
    # weight solvers
    "minimum_variance_weights",
    "tangency_weights",
    "target_return_weights",
    "efficient_frontier",
    "FrontierPoint",
    # weight statistics
    "portfolio_return_from_weights",
    "portfolio_variance_from_weights",
    "portfolio_volatility_from_weights",
    "portfolio_sharpe_from_weights",
    # PortfolioData entry points
    "minimum_variance_portfolio",
    "maximum_sharpe_portfolio",
    "efficient_frontier_portfolio",
    # rebalancing
    "RebalanceTrade",
    "rebalance_to_model",
    "rebalance_to_policy",
    "total_drift",
    # tax-aware lot selection
    "LotSaleMethod",
    "RealizedLot",
    "SaleResult",
    "select_lots_to_sell",
    # tax-loss harvesting
    "HarvestCandidate",
    "HarvestReport",
    "harvest_candidates",
    # cash-flow rebalancing
    "CashFlowPlan",
    "invest_cashflow",
    # tax-budgeted rebalancing
    "TaxRebalancePlan",
    "TaxRebalanceSell",
    "tax_aware_rebalance",
    "tax_aware_rebalance_to_policy",
]
