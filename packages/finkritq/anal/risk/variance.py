# finkrit/packages/finkritq/anal/variance.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.covariance import covariance_matrix
from finkritq.transform.returns import ReturnCalculationMethod, periodic_returns
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, WeightingBasis
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

    returns = periodic_returns(prices, method=method)

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
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX,
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
    basis
        CONSTANT_MIX (default) uses the ex-ante quadratic form wᵀΣw; BUY_AND_HOLD
        uses the variance of the realized value-path return series. See
        WeightingBasis.

    Returns
    -------
    float
        Portfolio variance.
    """

    # BUY_AND_HOLD: variance of the realized value-path return series. Weights
    # drift with prices, so there is no closed-form quadratic shortcut, take
    # the sample variance of the series directly.
    if basis == WeightingBasis.BUY_AND_HOLD:
        return variance_from_returns(
            portfolio_data.realized_returns(method),
            annualized=annualized,
            periods_per_year=periods_per_year,
        )

    # CONSTANT_MIX (default): weights are fixed at `w`, so the portfolio variance
    # is the exact quadratic form σ_p² = wᵀΣw. This equals the sample variance of
    # `constant_mix_returns` (linearity of variance) but computing it from Σ is
    # the canonical ex-ante form and is what MCTR/CCTR decompose.
    covariance = covariance_matrix(
        portfolio_data,
        method=method,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )

    weights = portfolio_data.weight_vector

    # σ_p² = wᵀΣw
    return float(weights.T @ covariance @ weights)

