# finkritintel/tool/asset.py

from finkritintel.tool.contract import ToolContract


ASSET_VOLATILITY = ToolContract(
    name="asset_volatility",
    description="Compute annualized volatility of an asset.",
    category="risk",
    tags=("asset", "volatility"),
)

ASSET_VARIANCE = ToolContract(
    name="asset_variance",
    description="Compute variance of an asset.",
    category="risk",
    tags=("asset", "variance"),
)

ASSET_SEMIVARIANCE = ToolContract(
    name="asset_semivariance",
    description="Compute semivariance of an asset.",
    category="risk",
    tags=("asset", "downside"),
)

ASSET_DOWNSIDE_DEVIATION = ToolContract(
    name="asset_downside_deviation",
    description="Compute downside deviation of an asset.",
    category="risk",
    tags=("asset", "downside"),
)

ASSET_DRAWDOWN = ToolContract(
    name="asset_drawdown",
    description="Compute drawdown series of an asset.",
    category="risk",
    tags=("asset", "drawdown"),
)

ASSET_MAXIMUM_DRAWDOWN = ToolContract(
    name="asset_maximum_drawdown",
    description="Compute maximum drawdown of an asset.",
    category="risk",
    tags=("asset", "drawdown"),
)

ASSET_VALUE_AT_RISK = ToolContract(
    name="asset_value_at_risk",
    description="Compute Value at Risk (VaR) of an asset.",
    category="risk",
    tags=("asset", "value-at-risk"),
)

ASSET_CONDITIONAL_VALUE_AT_RISK = ToolContract(
    name="asset_conditional_value_at_risk",
    description="Compute Conditional Value at Risk (CVaR) of an asset.",
    category="risk",
    tags=("asset", "value-at-risk"),
)

ASSET_BETA = ToolContract(
    name="asset_beta",
    description="Compute beta of an asset relative to a benchmark.",
    category="risk",
    tags=("asset", "beta"),
)

