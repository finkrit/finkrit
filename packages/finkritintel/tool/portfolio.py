# finkritintel/tool/portfolio.py

from finkritintel.tool.contract import ToolContract


PORTFOLIO_VOLATILITY = ToolContract(
    name="portfolio_volatility",
    description="Compute annualized portfolio volatility.",
    category="risk",
    tags=("portfolio", "volatility"),
)

PORTFOLIO_VARIANCE = ToolContract(
    name="portfolio_variance",
    description="Compute portfolio variance.",
    category="risk",
    tags=("portfolio", "variance"),
)

PORTFOLIO_SEMIVARIANCE = ToolContract(
    name="portfolio_semivariance",
    description="Compute portfolio semivariance.",
    category="risk",
    tags=("portfolio", "downside"),
)

PORTFOLIO_DOWNSIDE_DEVIATION = ToolContract(
    name="portfolio_downside_deviation",
    description="Compute portfolio downside deviation.",
    category="risk",
    tags=("portfolio", "downside"),
)

PORTFOLIO_DRAWDOWN = ToolContract(
    name="portfolio_drawdown",
    description="Compute portfolio drawdown series.",
    category="risk",
    tags=("portfolio", "drawdown"),
)

PORTFOLIO_MAXIMUM_DRAWDOWN = ToolContract(
    name="portfolio_maximum_drawdown",
    description="Compute portfolio maximum drawdown.",
    category="risk",
    tags=("portfolio", "drawdown"),
)

PORTFOLIO_VALUE_AT_RISK = ToolContract(
    name="portfolio_value_at_risk",
    description="Compute portfolio Value at Risk (VaR).",
    category="risk",
    tags=("portfolio", "value-at-risk"),
)

PORTFOLIO_CONDITIONAL_VALUE_AT_RISK = ToolContract(
    name="portfolio_conditional_value_at_risk",
    description="Compute portfolio Conditional Value at Risk (CVaR).",
    category="risk",
    tags=("portfolio", "value-at-risk"),
)

PORTFOLIO_BETA = ToolContract(
    name="portfolio_beta",
    description="Compute portfolio beta relative to a benchmark.",
    category="risk",
    tags=("portfolio", "beta"),
)

PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK = ToolContract(
    name="portfolio_marginal_contribution_to_risk",
    description="Compute marginal contribution to portfolio risk for each asset.",
    category="risk",
    tags=("portfolio", "contribution"),
)

PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK = ToolContract(
    name="portfolio_component_contribution_to_risk",
    description="Compute component contribution to portfolio risk for each asset.",
    category="risk",
    tags=("portfolio", "contribution"),
)

