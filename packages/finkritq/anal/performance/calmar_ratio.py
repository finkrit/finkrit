# finkritq/anal/performance/calmar_ratio.py
"""
Calmar ratio: annualized return per unit of worst peak-to-trough loss.

    calmar = annualized return / |maximum drawdown|

Where Sharpe and Sortino divide by a dispersion measure, Calmar divides by the
single worst drawdown, so it speaks to pain tolerance: how much growth did you
earn for the deepest loss you had to sit through. Standard Calmar takes no
risk-free rate.
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
from finkritq.anal.risk.drawdown import (
    maximum_drawdown_from_prices,
    portfolio_maximum_drawdown,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _calmar(annualized_return: float, maximum_drawdown: float) -> float:
    """
    Combine the annualized return with the maximum drawdown.

    `maximum_drawdown` is non-positive (a drawdown of -0.2 is a 20% loss). Returns
    nan when it is exactly zero: a series that never fell has no drawdown to
    divide by and the ratio is undefined.
    """

    if maximum_drawdown == 0.0:
        return float("nan")

    return annualized_return / abs(maximum_drawdown)


def calmar_ratio_from_returns(
    returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio from a periodic return series.

    The drawdown is taken off a reconstructed wealth path rather than
    maximum_drawdown_from_returns, for two reasons: a leading 1.0 is prepended so
    a first-period loss is counted, and the path is built per `method` (exp of the
    cumulative sum for log returns, cumulative product for simple) rather than
    compounding log returns as if they were simple. With that, this matches
    calmar_ratio_from_prices exactly (drawdown is scale-invariant).
    """

    annualized = annualized_return_from_returns(
        returns, method=method, periods_per_year=periods_per_year
    )

    if method == ReturnCalculationMethod.LOG:
        wealth = np.concatenate(([1.0], np.exp(np.cumsum(returns))))
    else:
        wealth = np.concatenate(([1.0], np.cumprod(1.0 + returns)))

    return _calmar(annualized, maximum_drawdown_from_prices(wealth))


def calmar_ratio_from_prices(
    prices: NDArray[np.float64],
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio from a price series.

    No `method`: both the annualized return and the drawdown are level-based and
    convention-free.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)

    return _calmar(annualized, maximum_drawdown_from_prices(prices))


def calmar_ratio(
    history: PriceHistory,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio from a PriceHistory.
    """

    return calmar_ratio_from_prices(history.close, periods_per_year=periods_per_year)


def calmar_ratio_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return calmar_ratio(history, periods_per_year=periods_per_year)


def portfolio_calmar_ratio(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio of a portfolio.

    `basis` is passed to BOTH the annualized return and the maximum drawdown, so
    the ratio describes one portfolio (see WeightingBasis). Defaults to
    BUY_AND_HOLD, the realized return over the realized worst drawdown.
    """

    annualized = portfolio_annualized_return(
        portfolio_data, basis=basis, periods_per_year=periods_per_year
    )
    max_dd = portfolio_maximum_drawdown(portfolio_data, basis=basis)

    return _calmar(annualized, max_dd)

