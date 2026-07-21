# finkritintel/tool/performance.py
"""
Tool contracts for the portfolio PERFORMANCE metrics (finkritq.anal.performance).

The risk contracts live in tool/portfolio.py; these are the return-magnitude and
risk-adjusted performance measures. The benchmark-relative trio (Treynor,
information ratio, Jensen's alpha) takes a benchmark, like portfolio beta.
"""

from finkritintel.tool.contract import ToolContract


PORTFOLIO_TOTAL_RETURN = ToolContract(
    name="portfolio_total_return",
    description="Compute the portfolio's total (cumulative) return over the window.",
    category="performance",
    tags=("portfolio", "return"),
)

PORTFOLIO_ANNUALIZED_RETURN = ToolContract(
    name="portfolio_annualized_return",
    description="Compute the portfolio's annualized (geometric/CAGR) return.",
    category="performance",
    tags=("portfolio", "return"),
)

PORTFOLIO_SHARPE_RATIO = ToolContract(
    name="portfolio_sharpe_ratio",
    description="Compute the portfolio Sharpe ratio (excess return per unit of total volatility).",
    category="performance",
    tags=("portfolio", "risk-adjusted"),
)

PORTFOLIO_SORTINO_RATIO = ToolContract(
    name="portfolio_sortino_ratio",
    description="Compute the portfolio Sortino ratio (excess return per unit of downside risk).",
    category="performance",
    tags=("portfolio", "risk-adjusted"),
)

PORTFOLIO_CALMAR_RATIO = ToolContract(
    name="portfolio_calmar_ratio",
    description="Compute the portfolio Calmar ratio (annualized return over maximum drawdown).",
    category="performance",
    tags=("portfolio", "risk-adjusted"),
)

PORTFOLIO_TREYNOR_RATIO = ToolContract(
    name="portfolio_treynor_ratio",
    description="Compute the portfolio Treynor ratio (excess return per unit of beta) vs a benchmark.",
    category="performance",
    tags=("portfolio", "risk-adjusted", "benchmark"),
)

PORTFOLIO_INFORMATION_RATIO = ToolContract(
    name="portfolio_information_ratio",
    description="Compute the portfolio information ratio (active return over tracking error) vs a benchmark.",
    category="performance",
    tags=("portfolio", "risk-adjusted", "benchmark"),
)

PORTFOLIO_JENSENS_ALPHA = ToolContract(
    name="portfolio_jensens_alpha",
    description="Compute the portfolio Jensen's alpha (return above the CAPM expectation) vs a benchmark.",
    category="performance",
    tags=("portfolio", "risk-adjusted", "benchmark"),
)
