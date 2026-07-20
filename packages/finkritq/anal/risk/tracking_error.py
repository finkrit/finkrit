# finkrit/packages/finkritq/anal/risk/tracking_error.py
"""
Tracking error: how much a portfolio's returns wander from a benchmark's.

    tracking_error = annualized std of (portfolio return - benchmark return)

It is the volatility of the ACTIVE return series (the period-by-period
difference from the benchmark), so it measures benchmark-relative risk: a fund
that mirrors its index has near-zero tracking error, an active bet has more. It
is the denominator of the information ratio.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.transform.returns import periodic_returns
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def tracking_error_from_returns(
    returns: NDArray[np.float64],
    benchmark_returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Tracking error from two aligned return series.

    Uses the sample standard deviation (ddof=1), matching volatility. Fewer than
    two active observations gives nan (no dispersion is estimable).
    """

    active = returns - benchmark_returns
    if len(active) < 2:
        return float("nan")

    tracking_error = np.std(active, ddof=1)
    if annualized:
        tracking_error *= np.sqrt(periods_per_year)

    return float(tracking_error)


def tracking_error_from_prices(
    prices: NDArray[np.float64],
    benchmark_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Tracking error from two aligned price series.
    """

    return tracking_error_from_returns(
        periodic_returns(prices, method),
        periodic_returns(benchmark_prices, method),
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def tracking_error(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Tracking error from two price histories, aligned on common dates.
    """

    history, benchmark_history = history.align(benchmark_history)

    return tracking_error_from_prices(
        history.close,
        benchmark_history.close,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def tracking_error_asset(
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
    Tracking error directly from two assets.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    asset_history = registry.history(asset, start=start, end=end, interval=interval)
    benchmark_history = registry.history(benchmark, start=start, end=end, interval=interval)

    return tracking_error(
        asset_history,
        benchmark_history,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def portfolio_tracking_error(
    portfolio_data: PortfolioData,
    benchmark: PriceHistory,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Tracking error of a portfolio against a benchmark.

    The portfolio return series (selected by `basis`) and the benchmark returns
    (aligned to the portfolio's dates) are differenced period-by-period. See
    WeightingBasis.
    """

    portfolio_returns = (
        portfolio_data.constant_mix_returns(method)
        if basis == WeightingBasis.CONSTANT_MIX
        else portfolio_data.realized_returns(method)
    )
    benchmark_returns = periodic_returns(portfolio_data.aligned_close(benchmark), method)

    return tracking_error_from_returns(
        portfolio_returns,
        benchmark_returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )
