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
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod
from finkritq.portfolio import Portfolio, PortfolioData

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
from .portfolio_schema_live import (
    PortfolioBetaLiveInput,
    PortfolioComponentRiskLiveInput,
    PortfolioConditionalValueAtRiskLiveInput,
    PortfolioDownsideDeviationLiveInput,
    PortfolioDrawdownLiveInput,
    PortfolioMarginalRiskLiveInput,
    PortfolioMaximumDrawdownLiveInput,
    PortfolioSemivarianeLiveInput,
    PortfolioValueAtRiskLiveInput,
    PortfolioVarianceLiveInput,
    PortfolioVolatilityLiveInput,
)


def _fetch(portfolio: Portfolio, registry: DataRegistry, start, end, interval) -> PortfolioData:
    return PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval=interval)


def _portfolio_volatility_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    method=ReturnCalculationMethod.LOG, annualized=True, periods_per_year=252,
) -> float:
    return portfolio_volatility(_fetch(portfolio, registry, start, end, interval), method=method, annualized=annualized, periods_per_year=periods_per_year)


def _portfolio_variance_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    method=ReturnCalculationMethod.LOG, annualized=True, periods_per_year=252,
) -> float:
    return portfolio_variance(_fetch(portfolio, registry, start, end, interval), method=method, annualized=annualized, periods_per_year=periods_per_year)


def _portfolio_semivariance_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    method=ReturnCalculationMethod.LOG, target=0.0, annualized=True, periods_per_year=252,
) -> float:
    return portfolio_semivariance(_fetch(portfolio, registry, start, end, interval), method=method, target=target, annualized=annualized, periods_per_year=periods_per_year)


def _portfolio_downside_deviation_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    method=ReturnCalculationMethod.LOG, target=0.0, annualized=True, periods_per_year=252,
) -> float:
    return portfolio_downside_deviation(_fetch(portfolio, registry, start, end, interval), method=method, target=target, annualized=annualized, periods_per_year=periods_per_year)


def _portfolio_drawdown_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
) -> NDArray[np.float64]:
    return portfolio_drawdown(_fetch(portfolio, registry, start, end, interval))


def _portfolio_maximum_drawdown_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
) -> float:
    return portfolio_maximum_drawdown(_fetch(portfolio, registry, start, end, interval))


def _portfolio_value_at_risk_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    return_method=ReturnCalculationMethod.LOG, method=None, confidence=0.95, n_simulations=100_000, random_state=None,
) -> float:
    from finkritq.datatype import VaREstimationMethod
    method = method or VaREstimationMethod.HISTORICAL
    return portfolio_value_at_risk(_fetch(portfolio, registry, start, end, interval), return_method=return_method, method=method, confidence=confidence, n_simulations=n_simulations, random_state=random_state)


def _portfolio_conditional_value_at_risk_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    return_method=ReturnCalculationMethod.LOG, method=None, confidence=0.95, n_simulations=100_000, random_state=None,
) -> float:
    from finkritq.datatype import VaREstimationMethod
    method = method or VaREstimationMethod.HISTORICAL
    return portfolio_conditional_value_at_risk(_fetch(portfolio, registry, start, end, interval), return_method=return_method, method=method, confidence=confidence, n_simulations=n_simulations, random_state=random_state)


def _portfolio_beta_live(
    portfolio: Portfolio, registry: DataRegistry,
    benchmark_history_or_asset: object,
    start=None, end=None, interval="1d",
    method=ReturnCalculationMethod.LOG,
) -> float:
    from finkritq.asset import Asset
    data = _fetch(portfolio, registry, start, end, interval)
    portfolio_returns = data.portfolio_returns(method=method)
    if isinstance(benchmark_history_or_asset, Asset):
        bh = registry.history(benchmark_history_or_asset, start=start, end=end, interval=interval)
    else:
        bh: PriceHistory = benchmark_history_or_asset
    benchmark_returns = calculate_returns(bh.close, method=method)
    return beta_from_returns(portfolio_returns, benchmark_returns)


def _portfolio_marginal_risk_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
) -> NDArray[np.float64]:
    return marginal_contribution_to_risk(_fetch(portfolio, registry, start, end, interval))


def _portfolio_component_risk_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
) -> NDArray[np.float64]:
    return component_contribution_to_risk(_fetch(portfolio, registry, start, end, interval))


PORTFOLIO_VOLATILITY_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_VOLATILITY,
    input_schema=PortfolioVolatilityLiveInput,
    output_schema=float,
    implementation=_portfolio_volatility_live,
)

PORTFOLIO_VARIANCE_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_VARIANCE,
    input_schema=PortfolioVarianceLiveInput,
    output_schema=float,
    implementation=_portfolio_variance_live,
)

PORTFOLIO_SEMIVARIANCE_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_SEMIVARIANCE,
    input_schema=PortfolioSemivarianeLiveInput,
    output_schema=float,
    implementation=_portfolio_semivariance_live,
)

PORTFOLIO_DOWNSIDE_DEVIATION_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_DOWNSIDE_DEVIATION,
    input_schema=PortfolioDownsideDeviationLiveInput,
    output_schema=float,
    implementation=_portfolio_downside_deviation_live,
)

PORTFOLIO_DRAWDOWN_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_DRAWDOWN,
    input_schema=PortfolioDrawdownLiveInput,
    output_schema=NDArray[np.float64],
    implementation=_portfolio_drawdown_live,
)

PORTFOLIO_MAXIMUM_DRAWDOWN_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_MAXIMUM_DRAWDOWN,
    input_schema=PortfolioMaximumDrawdownLiveInput,
    output_schema=float,
    implementation=_portfolio_maximum_drawdown_live,
)

PORTFOLIO_VALUE_AT_RISK_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_VALUE_AT_RISK,
    input_schema=PortfolioValueAtRiskLiveInput,
    output_schema=float,
    implementation=_portfolio_value_at_risk_live,
)

PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_CONDITIONAL_VALUE_AT_RISK,
    input_schema=PortfolioConditionalValueAtRiskLiveInput,
    output_schema=float,
    implementation=_portfolio_conditional_value_at_risk_live,
)

PORTFOLIO_BETA_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_BETA,
    input_schema=PortfolioBetaLiveInput,
    output_schema=float,
    implementation=_portfolio_beta_live,
)

PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK,
    input_schema=PortfolioMarginalRiskLiveInput,
    output_schema=NDArray[np.float64],
    implementation=_portfolio_marginal_risk_live,
)

PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK,
    input_schema=PortfolioComponentRiskLiveInput,
    output_schema=NDArray[np.float64],
    implementation=_portfolio_component_risk_live,
)
