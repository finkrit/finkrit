# finkrit/packages/finkritq/anal/performance/total_return.py
"""
Total (cumulative) return: the single figure "how much did this grow over the
whole window", e.g. 0.25 for a 25% gain from first observation to last.

Annualized return scales it to a per-year figure, 
and every risk-adjusted ratio (Sharpe, Sortino, Calmar etc.)
uses that annualized number as its numerator.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def total_return_from_returns(
    returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> float:
    """
    Compound a periodic return series into one cumulative total return.

    How a return series compounds depends on how it was defined, so the caller
    states the convention via `method`:

    LOG
        Log returns ADD across time. Their sum is the log of the overall wealth
        ratio, so the total return is exp(sum) minus 1.
    SIMPLE
        Simple returns compound MULTIPLICATIVELY. A period gain of r multiplies
        wealth by (1 + r), so cumulative growth is the product of (1 + r_t) and
        the total return is that product minus 1.

    Both are exact for a genuine return series of the matching convention. An
    empty series yields 0.0 (no periods, no growth).
    """

    if method == ReturnCalculationMethod.LOG:
        # exp(Σ log_t) - 1. expm1 is exp(x) - 1 computed accurately near zero.
        return float(np.expm1(np.sum(returns)))

    if method == ReturnCalculationMethod.SIMPLE:
        # Π (1 + r_t) - 1.
        return float(np.prod(1.0 + returns) - 1.0)

    raise ValueError(f"Unsupported return calculation method: {method}")


def total_return_from_prices(prices: NDArray[np.float64]) -> float:
    """
    Total return of a price series: the first-to-last ratio, P_last/P_first - 1.

    No compounding and no `method` here. With the endpoints in hand the answer is
    exact and convention-free. Compounding is only needed in
    total_return_from_returns, which is handed a return series and has no levels
    to divide.
    """

    return float(prices[-1] / prices[0] - 1.0)


def total_return(history: PriceHistory) -> float:
    """
    Compute total return from a PriceHistory.
    """

    return total_return_from_prices(history.close)


def total_return_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> float:
    """
    Compute total return directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return total_return(history)


def portfolio_total_return(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
) -> float:
    """
    Compute the total return of a portfolio.

    Total return is level-based, so there is no `method`. Each basis has exactly
    one correct construction.

    BUY_AND_HOLD (default)
        The realized growth of the actual value path, value_last/value_first - 1,
        taken straight from the value levels. Convention-free.
    CONSTANT_MIX
        A rebalanced portfolio's period return is the weighted sum of the SIMPLE
        asset returns, Σ_i w_i·r_i(t); total return compounds those. Log returns
        do not sum across assets, so SIMPLE is the only correct convention here.
    """

    if basis == WeightingBasis.CONSTANT_MIX:
        simple = portfolio_data.constant_mix_returns()
        return total_return_from_returns(simple, method=ReturnCalculationMethod.SIMPLE)

    value = portfolio_data.value
    return float(value[-1] / value[0] - 1.0)

