# finkrit/packages/finq/anal/risk/downside_deviation.py

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


def downside_deviation_from_returns(
    returns: NDArray[np.float64],
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the downside deviation of a return series.
    """

    downside = np.minimum(returns - target, 0.0)

    downside_deviation = np.sqrt(
        np.mean(np.square(downside))
    )

    if annualized:
        downside_deviation *= np.sqrt(periods_per_year)

    return float(downside_deviation)


def downside_deviation_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute downside deviation from a price series.
    """

    returns = calculate_returns(
        prices,
        method=method,
    )

    return downside_deviation_from_returns(
        returns,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def downside_deviation(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute downside deviation from a PriceHistory.
    """

    return downside_deviation_from_prices(
        history.close,
        method=method,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def downside_deviation_asset(
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
    Compute downside deviation directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    return downside_deviation(
        history,
        method=method,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )


def portfolio_downside_deviation(
    portfolio_data: PortfolioData,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute downside deviation of a portfolio.
    """

    returns = portfolio_data.portfolio_returns(
        method=method,
    )

    return downside_deviation_from_returns(
        returns,
        target=target,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

