from __future__ import annotations

from finkritq.anal.performance import (
    portfolio_annualized_return,
    portfolio_calmar_ratio,
    portfolio_sharpe_ratio,
    portfolio_sortino_ratio,
    portfolio_total_return,
)
from finkritq.data import DataRegistry
from finkritq.datatype import WeightingBasis
from finkritq.portfolio import Portfolio, PortfolioData

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.performance import (
    PORTFOLIO_ANNUALIZED_RETURN,
    PORTFOLIO_CALMAR_RATIO,
    PORTFOLIO_SHARPE_RATIO,
    PORTFOLIO_SORTINO_RATIO,
    PORTFOLIO_TOTAL_RETURN,
)
from finkritintel.integration.finkritq.performance_schema_live import (
    PortfolioAnnualizedReturnLiveInput,
    PortfolioCalmarRatioLiveInput,
    PortfolioSharpeRatioLiveInput,
    PortfolioSortinoRatioLiveInput,
    PortfolioTotalReturnLiveInput,
)


def _fetch(portfolio: Portfolio, registry: DataRegistry, start, end, interval) -> PortfolioData:
    return PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval=interval)


# Live wrappers fetch PortfolioData, then delegate to the finkritq function.
# Portfolio returns are always simple, so there is no return-convention `method`.


def _portfolio_total_return_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    basis=WeightingBasis.BUY_AND_HOLD,
) -> float:
    return portfolio_total_return(_fetch(portfolio, registry, start, end, interval), basis=basis)


def _portfolio_annualized_return_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    basis=WeightingBasis.BUY_AND_HOLD, periods_per_year=252,
) -> float:
    return portfolio_annualized_return(_fetch(portfolio, registry, start, end, interval), basis=basis, periods_per_year=periods_per_year)


def _portfolio_sharpe_ratio_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    basis=WeightingBasis.BUY_AND_HOLD, risk_free_rate=0.0, periods_per_year=252,
) -> float:
    return portfolio_sharpe_ratio(_fetch(portfolio, registry, start, end, interval), basis=basis, risk_free_rate=risk_free_rate, periods_per_year=periods_per_year)


def _portfolio_sortino_ratio_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    basis=WeightingBasis.BUY_AND_HOLD, risk_free_rate=0.0, target=0.0, periods_per_year=252,
) -> float:
    return portfolio_sortino_ratio(_fetch(portfolio, registry, start, end, interval), basis=basis, risk_free_rate=risk_free_rate, target=target, periods_per_year=periods_per_year)


def _portfolio_calmar_ratio_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d",
    basis=WeightingBasis.BUY_AND_HOLD, periods_per_year=252,
) -> float:
    return portfolio_calmar_ratio(_fetch(portfolio, registry, start, end, interval), basis=basis, periods_per_year=periods_per_year)


PORTFOLIO_TOTAL_RETURN_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_TOTAL_RETURN,
    input_schema=PortfolioTotalReturnLiveInput,
    output_schema=float,
    implementation=_portfolio_total_return_live,
)

PORTFOLIO_ANNUALIZED_RETURN_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_ANNUALIZED_RETURN,
    input_schema=PortfolioAnnualizedReturnLiveInput,
    output_schema=float,
    implementation=_portfolio_annualized_return_live,
)

PORTFOLIO_SHARPE_RATIO_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_SHARPE_RATIO,
    input_schema=PortfolioSharpeRatioLiveInput,
    output_schema=float,
    implementation=_portfolio_sharpe_ratio_live,
)

PORTFOLIO_SORTINO_RATIO_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_SORTINO_RATIO,
    input_schema=PortfolioSortinoRatioLiveInput,
    output_schema=float,
    implementation=_portfolio_sortino_ratio_live,
)

PORTFOLIO_CALMAR_RATIO_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_CALMAR_RATIO,
    input_schema=PortfolioCalmarRatioLiveInput,
    output_schema=float,
    implementation=_portfolio_calmar_ratio_live,
)
