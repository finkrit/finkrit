# finkrit/packages/finkritq/anal/performance/information_ratio.py
"""
Information ratio: active return per unit of active risk.

    information_ratio = (annualized return - annualized benchmark return)
                        / tracking error

It is to a benchmark what Sharpe is to cash: how much a manager beat the index
per unit of how far they strayed from it. A high information ratio means
consistent outperformance, not just a lucky year of large bets.
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
from finkritq.anal.risk.tracking_error import (
    portfolio_tracking_error,
    tracking_error_from_prices,
    tracking_error_from_returns,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _information_ratio(active_return: float, tracking_error: float) -> float:
    """
    Combine the annualized active return with the tracking error.

    Returns nan when tracking error is zero: the portfolio never deviated from
    the benchmark, so there is no active risk to divide by.
    """

    if tracking_error == 0.0:
        return float("nan")

    return active_return / tracking_error


def information_ratio_from_returns(
    returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Information ratio from an aligned return series and its benchmark's returns.
    """

    annualized = annualized_return_from_returns(returns, method=method, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_returns(
        benchmark_returns, method=method, periods_per_year=periods_per_year
    )
    tracking = tracking_error_from_returns(
        returns, benchmark_returns, annualized=True, periods_per_year=periods_per_year
    )

    return _information_ratio(annualized - benchmark_annualized, tracking)


def information_ratio_from_prices(
    prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Information ratio from an aligned price series and its benchmark's prices.

    The annualized-return terms are convention-free; `method` only affects the
    tracking-error denominator.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_prices(benchmark_prices, periods_per_year=periods_per_year)
    tracking = tracking_error_from_prices(
        prices, benchmark_prices, method=method, annualized=True, periods_per_year=periods_per_year
    )

    return _information_ratio(annualized - benchmark_annualized, tracking)


def information_ratio(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Information ratio from an asset history and a benchmark history.

    Histories are aligned on common dates first.
    """

    history, benchmark_history = history.align(benchmark_history)

    return information_ratio_from_prices(
        history.close,
        benchmark_history.close,
        method=method,
        periods_per_year=periods_per_year,
    )


def information_ratio_asset(
    asset: Asset,
    benchmark: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Information ratio directly from an asset and a benchmark asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(asset, start=start, end=end, interval=interval)
    benchmark_history = registry.history(benchmark, start=start, end=end, interval=interval)

    return information_ratio(
        asset_history,
        benchmark_history,
        method=method,
        periods_per_year=periods_per_year,
    )


def portfolio_information_ratio(
    portfolio_data: PortfolioData,
    benchmark: PriceHistory,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Information ratio of a portfolio against a benchmark.

    `basis` selects the portfolio return series (see WeightingBasis). The
    benchmark's annualized return is taken from its prices aligned to the
    portfolio's dates, so both return terms cover the same window.
    """

    annualized = portfolio_annualized_return(portfolio_data, basis=basis, periods_per_year=periods_per_year)
    benchmark_annualized = annualized_return_from_prices(
        portfolio_data.aligned_close(benchmark), periods_per_year=periods_per_year
    )
    tracking = portfolio_tracking_error(
        portfolio_data, benchmark, basis=basis, method=method, annualized=True, periods_per_year=periods_per_year
    )

    return _information_ratio(annualized - benchmark_annualized, tracking)
