# finkrit/packages/finkritq/anal/variance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.covariance import covariance_matrix
from finkritq.anal.returns import ReturnCalculationMethod, calculate_returns
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory
from finkritq.portfolio import PortfolioData


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


def portfolio_variance(
    portfolio_data: PortfolioData,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the variance of a portfolio.

    Parameters
    ----------
    portfolio_data
        Portfolio market data.

    Returns
    -------
    float
        Portfolio variance.
    """

    covariance = covariance_matrix(
        portfolio_data,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

    weights = portfolio_data.weight_vector

    # σp2​=w⊤Σw
    return float(weights.T @ covariance @ weights)

