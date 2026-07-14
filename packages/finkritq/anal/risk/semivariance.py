# finkrit/packages/finkritq/anal/risk/semivariance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from packages.finkritq.anal.returns import (ReturnCalculationMethod, calculate_returns)
from packages.finkritq.asset import Asset
from packages.finkritq.data import DataRegistry
from packages.finkritq.datatype import PriceHistory
from packages.finkritq.portfolio import PortfolioData


def semivariance_from_returns(
    returns: NDArray[np.float64],
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the semivariance of a return series.
    """

    downside = np.minimum(returns - target, 0.0)
    semivariance = np.mean(np.square(downside))

    if annualized:
        semivariance *= periods_per_year

    return float(semivariance)


def semivariance_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute semivariance from a price series.
    """

    returns = calculate_returns(prices, method=method)

    return semivariance_from_returns(
        returns,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def semivariance(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute semivariance from a PriceHistory.
    """

    return semivariance_from_prices(
        history.close,
        method=method,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def semivariance_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute semivariance directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    return semivariance(
        history,
        method=method,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def portfolio_semivariance(
    portfolio_data: PortfolioData,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the semivariance of a portfolio.
    """

    returns = portfolio_data.portfolio_returns(method=method)

    return semivariance_from_returns(
        returns,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )