# finkritintel/tool/risk.py
"""
The two risk contracts an agent actually drives.

The per metric contracts in ``asset.py`` and ``portfolio.py`` still exist and
still run, they are just no longer what a model chooses between. Nine metrics
across two scopes made twenty near identical descriptions carrying eleven
ideas, and every asset tool took a single ticker, so "the betas of my holdings"
was one call per holding. These two take lists instead.
"""

from finkritintel.tool.contract import ToolContract

# Descriptions are the whole interface for a model choosing a tool, so they
# name the metric vocabulary inline. A model should never have to infer that
# beta belongs to risk, it should read the word in the list.
_METRIC_NAMES = (
    "volatility, variance, semivariance, downside_deviation, value_at_risk, "
    "conditional_value_at_risk, beta, max_drawdown"
)

PORTFOLIO_RISK = ToolContract(
    name="portfolio_risk",
    description=(
        "Risk metrics for the portfolio as a whole. Pass `metrics` to pick from: "
        f"{_METRIC_NAMES}, drawdown, marginal_contribution, component_contribution. "
        "Omit `metrics` and every one is computed. The two contribution metrics "
        "break the portfolio's risk down across its holdings and exist only here, "
        "since a single asset has nothing to decompose. Beta uses the S&P 500 "
        "unless `benchmark_ticker` says otherwise. One call returns them all, so "
        "there is never a reason to ask for metrics one at a time."
    ),
    category="risk",
    tags=("portfolio", "risk", "multi-metric"),
)

ASSET_RISK = ToolContract(
    name="asset_risk",
    description=(
        "Risk metrics for individual holdings, one row per ticker. Omit `tickers` "
        "and every holding in the portfolio is covered, which is the right way to "
        "answer questions about 'my assets' or 'each stock' since you do not need "
        "to know the tickers. Pass `tickers` only to narrow to specific ones. "
        f"Pass `metrics` to pick from: {_METRIC_NAMES}. Omit `metrics` and every "
        "one is computed. The result names which metrics it computed and which "
        "were available but not requested, so check there before calling again."
    ),
    category="risk",
    tags=("asset", "risk", "multi-metric"),
)
