# finkrit/packages/finq/anal/covariance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.returns import ReturnCalculationMethod, calculate_returns
from packages.finq.asset import Asset
from packages.finq.data import DataRegistry
from packages.finq.datatype import PriceHistory


def covariance_from_returns(
    asset_returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the covariance between two aligned return series.
    """

    covariance = np.cov(asset_returns, benchmark_returns, ddof=1)[0, 1]
    if annualized:
        covariance *= periods_per_year

    return float(covariance)


def covariance_from_prices(
    asset_prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute covariance from two aligned price series.
    """

    asset_returns = calculate_returns(asset_prices, method=method)

    benchmark_returns = calculate_returns(benchmark_prices, method=method)
    return covariance_from_returns(
        asset_returns,
        benchmark_returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def covariance(
    asset_history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute covariance from two price histories.
    """

    asset_history, benchmark_history = asset_history.align(
        benchmark_history
    )

    return covariance_from_prices(
        asset_history.close,
        benchmark_history.close,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def covariance_asset(
    asset: Asset,
    benchmark: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute covariance directly from two assets.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    benchmark_history = registry.history(
        benchmark,
        start=start,
        end=end,
        interval=interval,
    )

    return covariance(
        asset_history,
        benchmark_history,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

