# finkrit/packages/finkritq/anal/performance/__init__.py
"""
Performance analytics: return magnitude and risk-adjusted performance.

Where anal/risk answers "how risky", this package answers "how much did it
return" and "how good was that return for the risk taken". It starts with raw
return magnitude (total, annualized) and builds up to the risk-adjusted ratios
(Sharpe, Sortino, Calmar, ...) that combine a return numerator with a risk
denominator from anal/risk.
"""
from finkritq.anal.performance.total_return import (
    portfolio_total_return,
    total_return,
    total_return_asset,
    total_return_from_prices,
    total_return_from_returns,
)
from finkritq.anal.performance.annualized_return import (
    annualized_return,
    annualized_return_asset,
    annualized_return_from_prices,
    annualized_return_from_returns,
    portfolio_annualized_return,
)
from finkritq.anal.performance.sharpe_ratio import (
    portfolio_sharpe_ratio,
    sharpe_ratio,
    sharpe_ratio_asset,
    sharpe_ratio_from_prices,
    sharpe_ratio_from_returns,
)
from finkritq.anal.performance.sortino_ratio import (
    portfolio_sortino_ratio,
    sortino_ratio,
    sortino_ratio_asset,
    sortino_ratio_from_prices,
    sortino_ratio_from_returns,
)
from finkritq.anal.performance.calmar_ratio import (
    calmar_ratio,
    calmar_ratio_asset,
    calmar_ratio_from_prices,
    calmar_ratio_from_returns,
    portfolio_calmar_ratio,
)

__all__ = [
    # total (cumulative) return
    "total_return_from_returns",
    "total_return_from_prices",
    "total_return",
    "total_return_asset",
    "portfolio_total_return",
    # annualized (geometric / CAGR) return
    "annualized_return_from_returns",
    "annualized_return_from_prices",
    "annualized_return",
    "annualized_return_asset",
    "portfolio_annualized_return",
    # sharpe ratio
    "sharpe_ratio_from_returns",
    "sharpe_ratio_from_prices",
    "sharpe_ratio",
    "sharpe_ratio_asset",
    "portfolio_sharpe_ratio",
    # sortino ratio
    "sortino_ratio_from_returns",
    "sortino_ratio_from_prices",
    "sortino_ratio",
    "sortino_ratio_asset",
    "portfolio_sortino_ratio",
    # calmar ratio
    "calmar_ratio_from_returns",
    "calmar_ratio_from_prices",
    "calmar_ratio",
    "calmar_ratio_asset",
    "portfolio_calmar_ratio",
]
