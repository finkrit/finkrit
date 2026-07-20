# finkrit/packages/finkritq/anal/covariance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.transform.returns import (
    ReturnCalculationMethod,
    periodic_returns,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory
from finkritq.portfolio import PortfolioData


def covariance_from_returns(
    asset_returns: NDArray[np.float64],
    other_asset_returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the covariance between two aligned return series.
    """

    covariance = np.cov(asset_returns, other_asset_returns, ddof=1)[0, 1]
    if annualized:
        covariance *= periods_per_year

    return float(covariance)


def covariance_from_prices(
    asset_prices: NDArray[np.float64],
    other_asset_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute covariance from two aligned price series.
    """

    asset_returns = periodic_returns(asset_prices, method=method)
    other_asset_returns = periodic_returns(other_asset_prices, method=method)

    return covariance_from_returns(
        asset_returns,
        other_asset_returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def covariance(
    asset_history: PriceHistory,
    other_asset_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute covariance from two price histories.
    """

    asset_history, other_asset_history = asset_history.align(other_asset_history)

    return covariance_from_prices(
        asset_history.close,
        other_asset_history.close,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def covariance_assets(
    asset: Asset,
    other_asset: Asset,
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

    other_asset_history = registry.history(
        other_asset,
        start=start,
        end=end,
        interval=interval,
    )

    return covariance(
        asset_history,
        other_asset_history,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def covariance_matrix_from_returns(
    returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> NDArray[np.float64]:
    """
    Compute the covariance matrix of multiple aligned return series.

    Parameters
    ----------
    returns
        Array of shape (n_assets, n_periods).
    """

    covariance = np.cov(returns, rowvar=True, ddof=1)

    if annualized:
        covariance *= periods_per_year

    return covariance


def covariance_matrix(
    portfolio_data: PortfolioData,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> NDArray[np.float64]:
    """
    Compute the covariance matrix of all assets in a portfolio.

    Uses SIMPLE asset returns and takes no `method`: this Σ feeds portfolio
    aggregation (wᵀΣw, MCTR/CCTR), which is only exact for simple returns. Pairwise
    `covariance`/`covariance_from_*` keep `method` for single-asset use.
    """

    returns = portfolio_data.return_matrix(ReturnCalculationMethod.SIMPLE)

    return covariance_matrix_from_returns(
        returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

