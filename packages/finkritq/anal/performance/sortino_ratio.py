# finkritq/anal/performance/sortino_ratio.py
"""
Sortino ratio: excess return per unit of DOWNSIDE risk.

    sortino = (annualized return - risk_free_rate) / downside deviation

Same shape as the Sharpe ratio, but the denominator is downside deviation
instead of total volatility, so only harmful (below-target) dispersion is
penalized. Upside swings, which an investor is happy to have, do not count
against the score.

Two thresholds sit at different horizons and are kept separate:
  risk_free_rate is an annual rate subtracted from the annualized numerator.
  target is the per-period minimum acceptable return (MAR) below which a period
  counts as downside for the denominator. Both default to 0.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.performance.annualized_return import (
    annualized_return_from_prices,
    annualized_return_from_returns,
    portfolio_annualized_return,
)
from finkritq.anal.risk.downside_deviation import (
    downside_deviation_from_prices,
    downside_deviation_from_returns,
    portfolio_downside_deviation,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _sortino(
    annualized_return: float,
    downside_deviation: float,
    risk_free_rate: float,
) -> float:
    """
    Combine the annualized excess return and the downside deviation.

    Returns nan when downside deviation is zero: no period fell below the target,
    so there is no downside risk to divide by and the ratio is undefined.
    """

    if downside_deviation == 0.0:
        return float("nan")

    return (annualized_return - risk_free_rate) / downside_deviation


def sortino_ratio_from_returns(
    returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sortino ratio from a periodic return series.
    """

    annualized = annualized_return_from_returns(
        returns, method=method, periods_per_year=periods_per_year
    )
    downside = downside_deviation_from_returns(
        returns, target=target, annualized=True, periods_per_year=periods_per_year
    )

    return _sortino(annualized, downside, risk_free_rate)


def sortino_ratio_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sortino ratio from a price series.

    The annualized-return numerator is convention-free; `method` only affects the
    downside-deviation denominator.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)
    downside = downside_deviation_from_prices(
        prices, method=method, target=target, annualized=True, periods_per_year=periods_per_year
    )

    return _sortino(annualized, downside, risk_free_rate)


def sortino_ratio(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sortino ratio from a PriceHistory.
    """

    return sortino_ratio_from_prices(
        history.close,
        method=method,
        risk_free_rate=risk_free_rate,
        target=target,
        periods_per_year=periods_per_year,
    )


def sortino_ratio_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sortino ratio directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return sortino_ratio(
        history,
        method=method,
        risk_free_rate=risk_free_rate,
        target=target,
        periods_per_year=periods_per_year,
    )


def portfolio_sortino_ratio(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sortino ratio of a portfolio.

    `basis` is passed to BOTH the annualized return and the downside deviation,
    so the ratio describes one portfolio (see WeightingBasis). Defaults to
    BUY_AND_HOLD. Portfolio returns are always simple, so there is no `method`.
    """

    annualized = portfolio_annualized_return(
        portfolio_data, basis=basis, periods_per_year=periods_per_year
    )
    downside = portfolio_downside_deviation(
        portfolio_data,
        basis=basis,
        target=target,
        annualized=True,
        periods_per_year=periods_per_year,
    )

    return _sortino(annualized, downside, risk_free_rate)
