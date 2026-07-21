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
from finkritq.anal.performance.treynor_ratio import (
    portfolio_treynor_ratio,
    treynor_ratio,
    treynor_ratio_asset,
    treynor_ratio_from_prices,
    treynor_ratio_from_returns,
)
from finkritq.anal.performance.information_ratio import (
    information_ratio,
    information_ratio_asset,
    information_ratio_from_prices,
    information_ratio_from_returns,
    portfolio_information_ratio,
)
from finkritq.anal.performance.jensens_alpha import (
    jensens_alpha,
    jensens_alpha_asset,
    jensens_alpha_from_prices,
    jensens_alpha_from_returns,
    portfolio_jensens_alpha,
)
from finkritq.anal.performance.flows import (
    money_weighted_return,
    time_weighted_return,
)
from finkritq.anal.performance.attribution import (
    AttributionResult,
    SegmentAttribution,
    brinson_attribution,
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
    # treynor ratio
    "treynor_ratio_from_returns",
    "treynor_ratio_from_prices",
    "treynor_ratio",
    "treynor_ratio_asset",
    "portfolio_treynor_ratio",
    # information ratio
    "information_ratio_from_returns",
    "information_ratio_from_prices",
    "information_ratio",
    "information_ratio_asset",
    "portfolio_information_ratio",
    # jensen's alpha
    "jensens_alpha_from_returns",
    "jensens_alpha_from_prices",
    "jensens_alpha",
    "jensens_alpha_asset",
    "portfolio_jensens_alpha",
    # cash-flow-aware returns
    "time_weighted_return",
    "money_weighted_return",
    # attribution
    "brinson_attribution",
    "AttributionResult",
    "SegmentAttribution",
]
