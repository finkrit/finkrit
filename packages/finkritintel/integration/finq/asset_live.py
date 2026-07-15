from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.beta import beta_asset
from finkritq.anal.risk.conditionalvalueatrisk import conditional_value_at_risk_asset
from finkritq.anal.risk.downside_deviation import downside_deviation_asset
from finkritq.anal.risk.drawdown import drawdown_asset, maximum_drawdown_asset
from finkritq.anal.risk.semivariance import semivariance_asset
from finkritq.anal.risk.valueatrisk import value_at_risk_asset
from finkritq.anal.risk.variance import variance_asset
from finkritq.anal.risk.volatility import volatility_asset

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.asset import (
    ASSET_BETA,
    ASSET_CONDITIONAL_VALUE_AT_RISK,
    ASSET_DOWNSIDE_DEVIATION,
    ASSET_DRAWDOWN,
    ASSET_MAXIMUM_DRAWDOWN,
    ASSET_SEMIVARIANCE,
    ASSET_VALUE_AT_RISK,
    ASSET_VARIANCE,
    ASSET_VOLATILITY,
)
from .asset_schema_live import (
    AssetBetaLiveInput,
    AssetConditionalValueAtRiskLiveInput,
    AssetDownsideDeviationLiveInput,
    AssetDrawdownLiveInput,
    AssetMaximumDrawdownLiveInput,
    AssetSemivarianeLiveInput,
    AssetValueAtRiskLiveInput,
    AssetVarianceLiveInput,
    AssetVolatilityLiveInput,
)


ASSET_VOLATILITY_LIVE_BINDING = ToolBinding(
    contract=ASSET_VOLATILITY,
    input_schema=AssetVolatilityLiveInput,
    output_schema=float,
    implementation=volatility_asset,
)

ASSET_VARIANCE_LIVE_BINDING = ToolBinding(
    contract=ASSET_VARIANCE,
    input_schema=AssetVarianceLiveInput,
    output_schema=float,
    implementation=variance_asset,
)

ASSET_SEMIVARIANCE_LIVE_BINDING = ToolBinding(
    contract=ASSET_SEMIVARIANCE,
    input_schema=AssetSemivarianeLiveInput,
    output_schema=float,
    implementation=semivariance_asset,
)

ASSET_DOWNSIDE_DEVIATION_LIVE_BINDING = ToolBinding(
    contract=ASSET_DOWNSIDE_DEVIATION,
    input_schema=AssetDownsideDeviationLiveInput,
    output_schema=float,
    implementation=downside_deviation_asset,
)

ASSET_DRAWDOWN_LIVE_BINDING = ToolBinding(
    contract=ASSET_DRAWDOWN,
    input_schema=AssetDrawdownLiveInput,
    output_schema=NDArray[np.float64],
    implementation=drawdown_asset,
)

ASSET_MAXIMUM_DRAWDOWN_LIVE_BINDING = ToolBinding(
    contract=ASSET_MAXIMUM_DRAWDOWN,
    input_schema=AssetMaximumDrawdownLiveInput,
    output_schema=float,
    implementation=maximum_drawdown_asset,
)

ASSET_VALUE_AT_RISK_LIVE_BINDING = ToolBinding(
    contract=ASSET_VALUE_AT_RISK,
    input_schema=AssetValueAtRiskLiveInput,
    output_schema=float,
    implementation=value_at_risk_asset,
)

ASSET_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING = ToolBinding(
    contract=ASSET_CONDITIONAL_VALUE_AT_RISK,
    input_schema=AssetConditionalValueAtRiskLiveInput,
    output_schema=float,
    implementation=conditional_value_at_risk_asset,
)

ASSET_BETA_LIVE_BINDING = ToolBinding(
    contract=ASSET_BETA,
    input_schema=AssetBetaLiveInput,
    output_schema=float,
    implementation=beta_asset,
)

