# finkrit/packages/finkritq/anal/performance/treynor_ratio.py
"""
Treynor ratio: excess return per unit of SYSTEMATIC risk.

    treynor = (annualized return - risk_free_rate) / beta

Like Sharpe, but the denominator is beta (market risk) instead of total
volatility. It rewards return earned per unit of exposure to the benchmark,
ignoring diversifiable risk, so it is the natural score for a holding viewed as
part of a larger, already-diversified book. Beta is a unitless regression
coefficient, so only the numerator is annualized.
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


def _treynor(annualized_return: float, beta: float, risk_free_rate: float) -> float:
    """
    Combine the annualized excess return with beta.

    Returns nan when beta is zero: no systematic exposure to divide by, so the
    ratio is undefined. (A nan beta from a degenerate benchmark propagates too.)
    """

    if beta == 0.0:
        return float("nan")

    return (annualized_return - risk_free_rate) / beta


def treynor_ratio_from_returns(
    returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Treynor ratio from an aligned return series and its benchmark's returns.
    """

    annualized = annualized_return_from_returns(
        returns, method=method, periods_per_year=periods_per_year
    )
    beta = beta_from_returns(returns, benchmark_returns)

    return _treynor(annualized, beta, risk_free_rate)


def treynor_ratio_from_prices(
    prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Treynor ratio from an aligned price series and its benchmark's prices.

    The annualized-return numerator is convention-free; `method` only affects the
    beta denominator.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)
    beta = beta_from_prices(prices, benchmark_prices, method=method)

    return _treynor(annualized, beta, risk_free_rate)


def treynor_ratio(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Treynor ratio from an asset history and a benchmark history.

    Histories are aligned on common dates first.
    """

    history, benchmark_history = history.align(benchmark_history)

    return treynor_ratio_from_prices(
        history.close,
        benchmark_history.close,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def treynor_ratio_asset(
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
    Treynor ratio directly from an asset and a benchmark asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(asset, start=start, end=end, interval=interval)
    benchmark_history = registry.history(benchmark, start=start, end=end, interval=interval)

    return treynor_ratio(
        asset_history,
        benchmark_history,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def portfolio_treynor_ratio(
    portfolio_data: PortfolioData,
    benchmark: PriceHistory,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Treynor ratio of a portfolio against a benchmark.

    `basis` selects the portfolio return series for BOTH the annualized return
    and the beta, so the ratio describes one portfolio (see WeightingBasis).
    Portfolio returns are always simple, so there is no `method`.
    """

    annualized = portfolio_annualized_return(
        portfolio_data, basis=basis, periods_per_year=periods_per_year
    )
    beta = portfolio_beta(portfolio_data, benchmark, basis=basis)

    return _treynor(annualized, beta, risk_free_rate)
