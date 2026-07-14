# finkrit/packages/finkritq/anal/risk/downside_deviation.py
"""
downside deviation is calculated = sqrt(semi-variance)
"""

from __future__ import annotations

from datetime import date

import numpy as np
from numpy.typing import NDArray

from packages.finkritq.anal.returns import ReturnCalculationMethod

from packages.finkritq.anal.risk.semivariance import (
    portfolio_semivariance,
    semivariance,
    semivariance_asset,
    semivariance_from_prices,
    semivariance_from_returns,
)

from packages.finkritq.asset import Asset
from packages.finkritq.data import DataRegistry
from packages.finkritq.datatype import PriceHistory
from packages.finkritq.portfolio import PortfolioData


def downside_deviation_from_returns(
    returns: NDArray[np.float64],
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the downside deviation of a return series.
    """

    return float(np.sqrt(
        semivariance_from_returns(
            returns,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))


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

    return float(np.sqrt(
        semivariance_from_prices(
            prices,
            method=method,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))


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

    return float(np.sqrt(
        semivariance(
            history,
            method=method,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))


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

    return float(np.sqrt(
        semivariance_asset(
            asset,
            registry,
            start=start,
            end=end,
            interval=interval,
            method=method,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))


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

    return float(np.sqrt(
        portfolio_semivariance(
            portfolio_data,
            method=method,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))

