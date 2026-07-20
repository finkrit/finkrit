# finkrit/packages/finkritq/anal/performance/annualized_return.py
"""
Annualized return (CAGR): the constant per-year growth rate that compounds to the
window's total return. A 21% gain over two years is not 10.5%/yr, it is
(1.21)^(1/2) - 1 = 10%/yr, because growth compounds.

This is the geometric annualized return, the "how fast did it actually grow per
year" figure. It is the numerator every risk-adjusted ratio (Sharpe, Sortino,
Calmar, ...) will scale against. It builds directly on total_return.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.performance.total_return import (
    portfolio_total_return,
    total_return_from_prices,
    total_return_from_returns,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _annualize(total_return: float, n_periods: int, periods_per_year: int) -> float:
    """
    Scale a window's total return to a constant per-year (geometric) rate.

    `n_periods` is the number of return periods (compounding intervals), NOT the
    number of price observations. `periods_per_year` says how many of those
    intervals make a year (252 trading days, 12 months, ...), so the window spans
    n_periods / periods_per_year years and:

        annualized = (1 + total_return) ** (1 / years) - 1

    A window shorter than one year is extrapolated to a full year (the exponent
    exceeds 1), which is standard but makes short-window figures volatile.
    """

    if n_periods <= 0:
        # No elapsed periods, so no growth rate to speak of.
        return 0.0

    base = 1.0 + total_return
    if base <= 0.0:
        # Wealth reached zero (or a nonsensical negative). A fractional power of a
        # non-positive base is not real, and total loss annualizes to -100%.
        return -1.0

    years = n_periods / periods_per_year
    return float(base ** (1.0 / years) - 1.0)


def annualized_return_from_returns(
    returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized (geometric) return from a periodic return series.

    `method` states how the series compounds (see total_return_from_returns). The
    period count is len(returns), one compounding interval per element.
    """

    total = total_return_from_returns(returns, method=method)
    return _annualize(total, len(returns), periods_per_year)


def annualized_return_from_prices(
    prices: NDArray[np.float64],
    periods_per_year: int = 252,
) -> float:
    """
    Annualized (geometric) return from a price series.

    No `method`: total return from prices is the convention-free endpoint ratio.
    m prices span m - 1 intervals, so that is the period count.
    """

    total = total_return_from_prices(prices)
    return _annualize(total, len(prices) - 1, periods_per_year)


def annualized_return(
    history: PriceHistory,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized (geometric) return from a PriceHistory.
    """

    return annualized_return_from_prices(history.close, periods_per_year=periods_per_year)


def annualized_return_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    periods_per_year: int = 252,
) -> float:
    """
    Annualized (geometric) return directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return annualized_return(history, periods_per_year=periods_per_year)


def portfolio_annualized_return(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized (geometric) return of a portfolio.

    `basis` selects which portfolio total return is annualized (see
    portfolio_total_return / WeightingBasis). Both bases share the same period
    count: the number of return intervals over the window, n_periods - 1.
    """

    total = portfolio_total_return(portfolio_data, basis=basis)
    return _annualize(total, portfolio_data.n_periods - 1, periods_per_year)

