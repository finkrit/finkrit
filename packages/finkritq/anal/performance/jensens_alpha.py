# finkrit/packages/finkritq/anal/performance/jensens_alpha.py
"""
Jensen's alpha: return earned above what CAPM says the risk taken deserved.

    alpha = annualized return - [rf + beta * (annualized benchmark return - rf)]

The bracket is the CAPM expected return for the portfolio's beta: the risk-free
rate plus beta times the market's excess return. Alpha is the gap between what
was actually earned and that fair expectation. Positive alpha is skill (or luck)
beyond simply dialing market exposure up or down. Unlike the ratios here, alpha
is itself a return (per year), not a dimensionless score.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.performance.annualized_return import (
    annualized_return_from_prices,
    annualized_return_from_returns,
    portfolio_annualized_return,
)
from finkritq.anal.risk.beta import beta_from_prices, beta_from_returns, portfolio_beta
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _alpha(
    annualized_return: float,
    benchmark_annualized_return: float,
    beta: float,
    risk_free_rate: float,
) -> float:
    """
    Actual annualized return minus the CAPM-expected return for this beta.
    """

    capm_expected = risk_free_rate + beta * (benchmark_annualized_return - risk_free_rate)
    return annualized_return - capm_expected


def jensens_alpha_from_returns(
    returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Jensen's alpha from an aligned return series and its benchmark's returns.
    """

    annualized = annualized_return_from_returns(returns, method=method, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_returns(
        benchmark_returns, method=method, periods_per_year=periods_per_year
    )
    beta = beta_from_returns(returns, benchmark_returns)

    return _alpha(annualized, benchmark_annualized, beta, risk_free_rate)


def jensens_alpha_from_prices(
    prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Jensen's alpha from an aligned price series and its benchmark's prices.

    The annualized-return terms are convention-free; `method` only affects beta.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_prices(benchmark_prices, periods_per_year=periods_per_year)
    beta = beta_from_prices(prices, benchmark_prices, method=method)

    return _alpha(annualized, benchmark_annualized, beta, risk_free_rate)


def jensens_alpha(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Jensen's alpha from an asset history and a benchmark history.

    Histories are aligned on common dates first.
    """

    history, benchmark_history = history.align(benchmark_history)

    return jensens_alpha_from_prices(
        history.close,
        benchmark_history.close,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def jensens_alpha_asset(
    asset: Asset,
    benchmark: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Jensen's alpha directly from an asset and a benchmark asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(asset, start=start, end=end, interval=interval)
    benchmark_history = registry.history(benchmark, start=start, end=end, interval=interval)

    return jensens_alpha(
        asset_history,
        benchmark_history,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def portfolio_jensens_alpha(
    portfolio_data: PortfolioData,
    benchmark: PriceHistory,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    risk_free_rate: float = 0.0,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Jensen's alpha of a portfolio against a benchmark.

    `basis` selects the portfolio return series for BOTH the annualized return
    and the beta (see WeightingBasis). The benchmark's annualized return is taken
    from its prices aligned to the portfolio's dates.
    """

    annualized = portfolio_annualized_return(portfolio_data, basis=basis, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_prices(
        portfolio_data.aligned_close(benchmark), periods_per_year=periods_per_year
    )
    beta = portfolio_beta(portfolio_data, benchmark, basis=basis, method=method)

    return _alpha(annualized, benchmark_annualized, beta, risk_free_rate)
