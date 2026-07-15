# finkrit/packages/finkritq/anal/risk/conditionalvalueatrisk.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm

from finkritq.anal.returns import calculate_returns
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import (
    PriceHistory,
    ReturnCalculationMethod,
    VaREstimationMethod,
)
from finkritq.portfolio import PortfolioData
from finkritq.anal.risk.valueatrisk import value_at_risk_from_returns


def conditional_value_at_risk_from_returns(
    returns: NDArray[np.float64],
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None,
) -> float:
    """
    Compute the Conditional Value at Risk (CVaR) from a return series.
    """

    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1.")

    if method == VaREstimationMethod.HISTORICAL:
        var = value_at_risk_from_returns(
            returns,
            method=VaREstimationMethod.HISTORICAL,
            confidence=confidence)

        tail = returns[returns <= -var]
        return float(-tail.mean())

    if method == VaREstimationMethod.PARAMETRIC:
        mean = returns.mean()
        std = returns.std(ddof=1)
        z = norm.ppf(1.0 - confidence)

        return float(-(mean - std * norm.pdf(z) / (1.0 - confidence)))

    if method == VaREstimationMethod.MONTE_CARLO:
        rng = np.random.default_rng(random_state)

        mean = returns.mean()
        std = returns.std(ddof=1)

        simulated_returns = rng.normal(
            loc=mean,
            scale=std,
            size=n_simulations)

        var = value_at_risk_from_returns(
            simulated_returns,
            method=VaREstimationMethod.HISTORICAL,
            confidence=confidence)

        tail = simulated_returns[simulated_returns <= -var]
        return float(-tail.mean())

    raise NotImplementedError(f"{method.value} Conditional Value at Risk is not implemented.")


def conditional_value_at_risk_from_prices(
    prices: NDArray[np.float64],
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Conditional Value at Risk (CVaR) from a price series.
    """

    returns = calculate_returns(prices, method=return_method)

    return conditional_value_at_risk_from_returns(
        returns,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )


def conditional_value_at_risk(
    history: PriceHistory,
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Conditional Value at Risk (CVaR) from a PriceHistory.
    """

    return conditional_value_at_risk_from_prices(
        history.close,
        return_method=return_method,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )


def conditional_value_at_risk_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Conditional Value at Risk (CVaR) directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    return conditional_value_at_risk(
        history,
        return_method=return_method,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )


def portfolio_conditional_value_at_risk(
    portfolio_data: PortfolioData,
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL,
    confidence: float = 0.95,
    n_simulations: int = 100_000,
    random_state: int | None = None) -> float:
    """
    Compute the Conditional Value at Risk (CVaR) of a portfolio.
    """

    returns = portfolio_data.portfolio_returns(method=return_method)

    return conditional_value_at_risk_from_returns(
        returns,
        method=method,
        confidence=confidence,
        n_simulations=n_simulations,
        random_state=random_state,
    )

