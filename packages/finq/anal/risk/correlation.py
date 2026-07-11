# finkrit/packages/finq/anal/risk/correlation.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.returns import (
    ReturnCalculationMethod,
    calculate_returns,
)
from packages.finq.asset import Asset
from packages.finq.data import DataRegistry
from packages.finq.datatype import PriceHistory
from packages.finq.portfolio import PortfolioData


def correlation_from_returns(
    asset_returns: NDArray[np.float64],
    other_asset_returns: NDArray[np.float64],
) -> float:
    """
    Compute the correlation between two aligned return series.
    """

    return float(np.corrcoef(asset_returns, other_asset_returns)[0, 1])


def correlation_from_prices(
    asset_prices: NDArray[np.float64],
    other_asset_prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute correlation from two aligned price series.
    """

    asset_returns = calculate_returns(asset_prices, method=method)
    other_asset_returns = calculate_returns(other_asset_prices, method=method)

    return correlation_from_returns(asset_returns, other_asset_returns)


def correlation(
    asset_history: PriceHistory,
    other_asset_history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute correlation from two price histories.
    """

    asset_history, other_asset_history = asset_history.align(
        other_asset_history
    )

    return correlation_from_prices(asset_history.close, other_asset_history.close, method=method)


def correlation_assets(
    asset: Asset,
    other_asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compute correlation directly from two assets.
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

    return correlation(
        asset_history,
        other_asset_history,
        method=method,
    )


def correlation_matrix_from_returns(
    returns: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute the correlation matrix of multiple aligned return series.

    Parameters
    ----------
    returns
        Array of shape (n_assets, n_periods).
    """

    return np.corrcoef(returns, rowvar=True)


def correlation_matrix(
    portfolio_data: PortfolioData,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> NDArray[np.float64]:
    """
    Compute the correlation matrix of all assets in a portfolio.
    """

    returns = portfolio_data.return_matrix(method)

    return correlation_matrix_from_returns(returns)

