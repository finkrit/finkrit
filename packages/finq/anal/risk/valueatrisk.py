# finkrit/packages/finq/anal/risk/valueatrisk.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm


from packages.finq.asset import Asset
from packages.finq.data import DataRegistry
from packages.finq.datatype import (
    PriceHistory,
    ReturnCalculationMethod,
    VaREstimationMethod,
)
from packages.finq.portfolio import PortfolioData
from packages.finq.anal.returns import calculate_returns


def value_at_risk_from_returns(
    returns: NDArray[np.float64],
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Value at Risk (value_at_risk) from a return series.
    """

    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1.")

    if method == VaREstimationMethod.HISTORICAL:
        percentile = 100.0 * (1.0 - confidence)
        return float(-np.percentile(returns, percentile))

    if method == VaREstimationMethod.PARAMETRIC:
        mean = returns.mean()
        std = returns.std(ddof=1)
        z = norm.ppf(1.0 - confidence)
        return float(-(mean + z * std))

    if method == VaREstimationMethod.MONTE_CARLO:
        rng = np.random.default_rng(random_state)

        mean = returns.mean()
        std = returns.std(ddof=1)

        simulated_returns = rng.normal(loc=mean, scale=std, size=n_simulations)

        percentile = 100.0 * (1.0 - confidence)
        return float(-np.percentile(simulated_returns, percentile))

    raise NotImplementedError(f"{method.value} value_at_risk is not implemented.")


def value_at_risk_from_prices(
    prices: NDArray[np.float64],
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Value at Risk (value_at_risk) from a price series.
    """

    returns = calculate_returns(prices, method=return_method)

    return value_at_risk_from_returns(
        returns,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state)


def value_at_risk(
    history: PriceHistory,
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Value at Risk (value_at_risk) from a PriceHistory.
    """

    return value_at_risk_from_prices(
        history.close,
        return_method=return_method,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )


def value_at_risk_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None,
) -> float:
    """
    Compute the Value at Risk (value_at_risk) directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(asset, start=start, end=end, interval=interval)

    return value_at_risk(
        history,
        return_method=return_method,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )


def portfolio_value_at_risk(
    portfolio_data: PortfolioData,
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Value at Risk (value_at_risk) of a portfolio.
    """

    returns = portfolio_data.portfolio_returns(method=return_method)

    return value_at_risk_from_returns(
        returns,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )

