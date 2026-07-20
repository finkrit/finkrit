# finkrit/packages/finkritq/anal/risk/downside_deviation.py
"""
downside deviation is calculated = sqrt(semi-variance)
"""

from __future__ import annotations

from datetime import date

import numpy as np
from numpy.typing import NDArray

from finkritq.transform.returns import ReturnCalculationMethod

from finkritq.anal.risk.semivariance import (
    portfolio_semivariance,
    semivariance,
    semivariance_asset,
    semivariance_from_prices,
    semivariance_from_returns,
)

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, WeightingBasis
from finkritq.portfolio import PortfolioData


def downside_deviation_from_returns(
    returns: NDArray[np.float64],
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252, # number of trading days
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
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    target: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute downside deviation of a portfolio.

    `basis` selects the realized (BUY_AND_HOLD, default) or ex-ante
    (CONSTANT_MIX) return basis; see WeightingBasis. Portfolio returns are always
    simple, so there is no `method`.
    """

    return float(np.sqrt(
        portfolio_semivariance(
            portfolio_data,
            basis=basis,
            target=target,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )
    ))

