# finkritq/anal/performance/sharpe_ratio.py
"""
Sharpe ratio: excess return per unit of total risk, the canonical risk-adjusted
performance measure.

    sharpe = (annualized return - risk_free_rate) / annualized volatility

This is the first metric that spans both analytics families: the numerator comes
from performance (annualized return) and the denominator from risk (volatility).

Two conventions, both deliberate:

  Numerator is the GEOMETRIC annualized return (CAGR), matching the rest of the
  performance layer and what a client sees, rather than the arithmetic annualized
  mean of excess returns that a textbook Sharpe often uses. risk_free_rate is an
  annual rate and is subtracted directly, since both terms are already per-year.

  For a portfolio the numerator and denominator MUST come from the same
  WeightingBasis, or the ratio divides one portfolio's return by another's risk.
  So portfolio_sharpe_ratio passes a single basis to both. This is the reason the
  risk layer's basis was made explicit before any ratio was built.
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
from finkritq.anal.risk.volatility import (
    portfolio_volatility,
    volatility_from_prices,
    volatility_from_returns,
)
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, ReturnCalculationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


def _sharpe(
    annualized_return: float,
    annualized_volatility: float,
    risk_free_rate: float,
) -> float:
    """
    Combine the annualized excess return and annualized volatility.

    Returns nan when volatility is zero: with no dispersion there is nothing to
    divide by and the ratio is undefined (a riskless series has no Sharpe).
    """

    if annualized_volatility == 0.0:
        return float("nan")

    return (annualized_return - risk_free_rate) / annualized_volatility


def sharpe_ratio_from_returns(
    returns: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio from a periodic return series.

    `method` states how the series compounds for the annualized-return numerator
    (volatility does not depend on it).
    """

    annualized = annualized_return_from_returns(
        returns, method=method, periods_per_year=periods_per_year
    )
    vol = volatility_from_returns(returns, annualized=True, periods_per_year=periods_per_year)

    return _sharpe(annualized, vol, risk_free_rate)


def sharpe_ratio_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio from a price series.

    The annualized-return numerator is convention-free (endpoint ratio); `method`
    only affects the volatility denominator.
    """

    annualized = annualized_return_from_prices(prices, periods_per_year=periods_per_year)
    vol = volatility_from_prices(
        prices, method=method, annualized=True, periods_per_year=periods_per_year
    )

    return _sharpe(annualized, vol, risk_free_rate)


def sharpe_ratio(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio from a PriceHistory.
    """

    return sharpe_ratio_from_prices(
        history.close,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def sharpe_ratio_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return sharpe_ratio(
        history,
        method=method,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )


def portfolio_sharpe_ratio(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Sharpe ratio of a portfolio.

    `basis` is passed to BOTH the annualized return and the volatility, so the
    ratio describes one portfolio (see WeightingBasis). Defaults to BUY_AND_HOLD:
    the realized return over the realized risk, the "how well did this book
    actually do per unit of risk" Sharpe. Portfolio returns are always simple, so
    there is no `method`.
    """

    annualized = portfolio_annualized_return(
        portfolio_data, basis=basis, periods_per_year=periods_per_year
    )
    vol = portfolio_volatility(
        portfolio_data,
        basis=basis,
        annualized=True,
        periods_per_year=periods_per_year,
    )

    return _sharpe(annualized, vol, risk_free_rate)

