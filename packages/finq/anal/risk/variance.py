# finkrit/packages/finq/anal/variance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.returns import ReturnCalculationMethod, calculate_returns
from packages.finq.asset import Asset
from packages.finq.data import DataRegistry
from packages.finq.datatype import PriceHistory


def variance_from_returns(
    returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the variance of a return series.
    """

    variance = np.var(returns, ddof=1)
    if annualized:
        variance *= periods_per_year

    return float(variance)


def variance_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute variance from a price series.
    """

    returns = calculate_returns(prices, method=method)

    return variance_from_returns(
        returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def variance(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute variance from a PriceHistory.
    """

    return variance_from_prices(
        history.close,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def variance_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute variance directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return variance(
        history,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

