# finkrit/packages/finkritq/anal/risk
"""
Volatility defined by:  σ = sqrt(Var(r)×252)
"""
from datetime import date, timedelta
import numpy as np
from numpy.typing import NDArray


from finkritq.transform.returns import periodic_returns, ReturnCalculationMethod
from finkritq.anal.risk.variance import portfolio_variance
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PriceHistory, WeightingBasis
from finkritq.portfolio import PortfolioData


def volatility_from_returns(
    returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the volatility of a return series.
    """

    variance = np.var(returns, ddof=1)
    volatility = np.sqrt(variance)
    if annualized:
        volatility *= np.sqrt(periods_per_year)
    return float(volatility)


def volatility_from_prices(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute volatility from a price series.
    """

    returns = periodic_returns(prices, method=method)
    return volatility_from_returns(returns, annualized=annualized, periods_per_year=periods_per_year)


def volatility(
    history: PriceHistory,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute volatility from a PriceHistory.
    """

    return volatility_from_prices(history.close, method=method, annualized=annualized, periods_per_year=periods_per_year)


def volatility_asset(
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
    Compute volatility directly from an asset.
    """
    end = end or date.today()
    start = start or end - timedelta(days=365)
    history = registry.history(asset, start=start, end=end, interval=interval)
    return volatility(history, method=method, annualized=annualized, periods_per_year=periods_per_year)



def portfolio_volatility(
    portfolio_data: PortfolioData,
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX,
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Compute the volatility of a portfolio.

    `basis` selects the ex-ante (CONSTANT_MIX, default) or realized
    (BUY_AND_HOLD) return basis; see WeightingBasis.
    """

    return float(np.sqrt(
        portfolio_variance(
            portfolio_data,
            basis=basis,
            method=method,
            annualized=annualized,
            periods_per_year=periods_per_year,
        )))

