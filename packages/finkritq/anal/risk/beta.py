# finkrit/packages/finkritq/analytics/risk.py

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from finkritq.transform.returns import periodic_returns
from finkritq.asset import Asset
from finkritq.datatype import (
    PriceHistory,
    ReturnCalculationMethod,
    WeightingBasis,
)
from finkritq.portfolio import PortfolioData

if TYPE_CHECKING:
    from finkritq.data.registry import DataRegistry


def beta_from_returns(
    asset_returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
) -> float:
    """
    Compute beta from two aligned return series.

    Beta is undefined (nan) without dispersion to regress against: fewer than two
    observations, or a benchmark with zero variance. The length guard also keeps
    np.cov(ddof=1) from dividing by n-1 = 0 and emitting a RuntimeWarning.
    """
    if len(benchmark_returns) < 2:
        return float("nan")

    covariance = np.cov(asset_returns, benchmark_returns, ddof=1)
    market_variance = covariance[1, 1]

    if market_variance == 0:
        return float("nan")
    return covariance[0, 1] / market_variance


def beta_from_prices(
    asset_prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute beta from two aligned price series.
    """

    asset_returns = periodic_returns(asset_prices, method=method)

    benchmark_returns = periodic_returns(benchmark_prices, method=method)
    return beta_from_returns(asset_returns, benchmark_returns)


def beta(
    asset_history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute beta from two price histories.

    Histories are automatically aligned on common dates.
    """
    asset_history, benchmark_history = asset_history.align(benchmark_history)
    return beta_from_prices(asset_history.close, benchmark_history.close, method=method,)


def beta_asset(
    asset: Asset,
    benchmark: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute beta directly from assets.
    """
    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(asset, start=start, end=end, interval=interval)
    benchmark_history = registry.history(benchmark, start=start,end=end, interval=interval)

    return beta(asset_history, benchmark_history, method=method)


def portfolio_beta(
    portfolio_data: PortfolioData,
    benchmark: PriceHistory,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute the beta of a portfolio against a benchmark.

    The portfolio's return series (selected by `basis`, see WeightingBasis) is
    regressed on the benchmark's returns. The benchmark is aligned to the
    portfolio's observation dates first, so the two series line up period-for-
    period.
    """
    portfolio_returns = (
        portfolio_data.constant_mix_returns(method)
        if basis == WeightingBasis.CONSTANT_MIX
        else portfolio_data.realized_returns(method)
    )
    benchmark_returns = periodic_returns(portfolio_data.aligned_close(benchmark), method)

    return beta_from_returns(portfolio_returns, benchmark_returns)

