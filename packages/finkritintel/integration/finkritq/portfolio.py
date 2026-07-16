from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.returns import calculate_returns
from finkritq.anal.risk.beta import beta_from_returns
from finkritq.anal.risk.componentrisk import component_contribution_to_risk
from finkritq.anal.risk.conditionalvalueatrisk import portfolio_conditional_value_at_risk
from finkritq.anal.risk.downside_deviation import portfolio_downside_deviation
from finkritq.anal.risk.drawdown import portfolio_drawdown, portfolio_maximum_drawdown
from finkritq.anal.risk.marginalrisk import marginal_contribution_to_risk
from finkritq.anal.risk.semivariance import portfolio_semivariance
from finkritq.anal.risk.valueatrisk import portfolio_value_at_risk
from finkritq.anal.risk.variance import portfolio_variance
from finkritq.anal.risk.volatility import portfolio_volatility
from finkritq.datatype import PriceHistory, ReturnCalculationMethod
from finkritq.portfolio import PortfolioData

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.portfolio import (
    PORTFOLIO_BETA,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK,
    PORTFOLIO_DOWNSIDE_DEVIATION,
    PORTFOLIO_DRAWDOWN,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK,
    PORTFOLIO_MAXIMUM_DRAWDOWN,
    PORTFOLIO_SEMIVARIANCE,
    PORTFOLIO_VALUE_AT_RISK,
    PORTFOLIO_VARIANCE,
    PORTFOLIO_VOLATILITY,
)
from finkritintel.integration.finkritq.portfolio_schema import (
    BetaInput,
    ComponentRiskInput,
    ConditionalValueAtRiskInput,
    DownsideDeviationInput,
    DrawdownInput,
    MarginalRiskInput,
    MaximumDrawdownInput,
    SemivarianceInput,
    ValueAtRiskInput,
    VarianceInput,
    VolatilityInput,
)


def _portfolio_beta(
    portfolio_data: PortfolioData,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    portfolio_returns = portfolio_data.portfolio_returns(method=method)
    benchmark_returns = calculate_returns(benchmark_history.close, method=method)
    return beta_from_returns(portfolio_returns, benchmark_returns)


PORTFOLIO_VOLATILITY_BINDING = ToolBinding(
    contract=PORTFOLIO_VOLATILITY,
    input_schema=VolatilityInput,
    output_schema=float,
    implementation=portfolio_volatility,
)

PORTFOLIO_VARIANCE_BINDING = ToolBinding(
    contract=PORTFOLIO_VARIANCE,
    input_schema=VarianceInput,
    output_schema=float,
    implementation=portfolio_variance,
)

PORTFOLIO_SEMIVARIANCE_BINDING = ToolBinding(
    contract=PORTFOLIO_SEMIVARIANCE,
    input_schema=SemivarianceInput,
    output_schema=float,
    implementation=portfolio_semivariance,
)

PORTFOLIO_DOWNSIDE_DEVIATION_BINDING = ToolBinding(
    contract=PORTFOLIO_DOWNSIDE_DEVIATION,
    input_schema=DownsideDeviationInput,
    output_schema=float,
    implementation=portfolio_downside_deviation,
)

PORTFOLIO_DRAWDOWN_BINDING = ToolBinding(
    contract=PORTFOLIO_DRAWDOWN,
    input_schema=DrawdownInput,
    output_schema=NDArray[np.float64],
    implementation=portfolio_drawdown,
)

PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING = ToolBinding(
    contract=PORTFOLIO_MAXIMUM_DRAWDOWN,
    input_schema=MaximumDrawdownInput,
    output_schema=float,
    implementation=portfolio_maximum_drawdown,
)

PORTFOLIO_VALUE_AT_RISK_BINDING = ToolBinding(
    contract=PORTFOLIO_VALUE_AT_RISK,
    input_schema=ValueAtRiskInput,
    output_schema=float,
    implementation=portfolio_value_at_risk,
)

PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING = ToolBinding(
    contract=PORTFOLIO_CONDITIONAL_VALUE_AT_RISK,
    input_schema=ConditionalValueAtRiskInput,
    output_schema=float,
    implementation=portfolio_conditional_value_at_risk,
)

PORTFOLIO_BETA_BINDING = ToolBinding(
    contract=PORTFOLIO_BETA,
    input_schema=BetaInput,
    output_schema=float,
    implementation=_portfolio_beta,
)

PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING = ToolBinding(
    contract=PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK,
    input_schema=MarginalRiskInput,
    output_schema=NDArray[np.float64],
    implementation=marginal_contribution_to_risk,
)

PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING = ToolBinding(
    contract=PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK,
    input_schema=ComponentRiskInput,
    output_schema=NDArray[np.float64],
    implementation=component_contribution_to_risk,
)
