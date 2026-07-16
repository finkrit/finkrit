# finkritintel/integration/finq/asset.py

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.beta import beta
from finkritq.anal.risk.conditionalvalueatrisk import conditional_value_at_risk
from finkritq.anal.risk.downside_deviation import downside_deviation
from finkritq.anal.risk.drawdown import drawdown, maximum_drawdown
from finkritq.anal.risk.semivariance import semivariance
from finkritq.anal.risk.valueatrisk import value_at_risk
from finkritq.anal.risk.variance import variance
from finkritq.anal.risk.volatility import volatility

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
from .asset_schema import (
    AssetBetaInput,
    AssetConditionalValueAtRiskInput,
    AssetDownsideDeviationInput,
    AssetDrawdownInput,
    AssetMaximumDrawdownInput,
    AssetSemivarianceInput,
    AssetValueAtRiskInput,
    AssetVarianceInput,
    AssetVolatilityInput,
)


ASSET_VOLATILITY_BINDING = ToolBinding(
    contract=ASSET_VOLATILITY,
    input_schema=AssetVolatilityInput,
    output_schema=float,
    implementation=volatility,
)

ASSET_VARIANCE_BINDING = ToolBinding(
    contract=ASSET_VARIANCE,
    input_schema=AssetVarianceInput,
    output_schema=float,
    implementation=variance,
)

ASSET_SEMIVARIANCE_BINDING = ToolBinding(
    contract=ASSET_SEMIVARIANCE,
    input_schema=AssetSemivarianceInput,
    output_schema=float,
    implementation=semivariance,
)

ASSET_DOWNSIDE_DEVIATION_BINDING = ToolBinding(
    contract=ASSET_DOWNSIDE_DEVIATION,
    input_schema=AssetDownsideDeviationInput,
    output_schema=float,
    implementation=downside_deviation,
)

ASSET_DRAWDOWN_BINDING = ToolBinding(
    contract=ASSET_DRAWDOWN,
    input_schema=AssetDrawdownInput,
    output_schema=NDArray[np.float64],
    implementation=drawdown,
)

ASSET_MAXIMUM_DRAWDOWN_BINDING = ToolBinding(
    contract=ASSET_MAXIMUM_DRAWDOWN,
    input_schema=AssetMaximumDrawdownInput,
    output_schema=float,
    implementation=maximum_drawdown,
)

ASSET_VALUE_AT_RISK_BINDING = ToolBinding(
    contract=ASSET_VALUE_AT_RISK,
    input_schema=AssetValueAtRiskInput,
    output_schema=float,
    implementation=value_at_risk,
)

ASSET_CONDITIONAL_VALUE_AT_RISK_BINDING = ToolBinding(
    contract=ASSET_CONDITIONAL_VALUE_AT_RISK,
    input_schema=AssetConditionalValueAtRiskInput,
    output_schema=float,
    implementation=conditional_value_at_risk,
)


ASSET_BETA_BINDING = ToolBinding(
    contract=ASSET_BETA,
    input_schema=AssetBetaInput,
    output_schema=float,
    implementation=beta,
)


