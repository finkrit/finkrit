# finkrit/packages/finq/anal/risk/drawdown.py

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from packages.finq.asset import Asset
from packages.finq.data import DataRegistry
from packages.finq.datatype import PriceHistory
from packages.finq.portfolio import PortfolioData


def drawdown_from_wealth(
    wealth: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute the drawdown series from a wealth index.

    Parameters
    ----------
    wealth
        Wealth or price series.

    Returns
    -------
    ndarray
        Drawdown series.
    """

    running_peak = np.maximum.accumulate(wealth)
    return (wealth - running_peak) / running_peak


def drawdown_from_returns(
    returns: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute the drawdown series from a return series.
    """

    wealth = np.cumprod(1.0 + returns)
    return drawdown_from_wealth(wealth)


def drawdown_from_prices(
    prices: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute the drawdown series from a price series.
    """

    return drawdown_from_wealth(prices)


def drawdown(
    history: PriceHistory,
) -> NDArray[np.float64]:
    """
    Compute the drawdown series from a PriceHistory.
    """

    return drawdown_from_prices(history.close)


def drawdown_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> NDArray[np.float64]:
    """
    Compute the drawdown series directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    return drawdown(history)


def maximum_drawdown_from_drawdown(
    drawdown: NDArray[np.float64],
) -> float:
    """
    Compute the maximum drawdown from a drawdown series.
    """

    return float(drawdown.min())


def maximum_drawdown_from_wealth(
    wealth: NDArray[np.float64],
) -> float:
    """
    Compute the maximum drawdown from a wealth series.
    """

    return maximum_drawdown_from_drawdown(
        drawdown_from_wealth(wealth)
    )


def maximum_drawdown_from_returns(
    returns: NDArray[np.float64],
) -> float:
    """
    Compute the maximum drawdown from a return series.
    """

    return maximum_drawdown_from_drawdown(
        drawdown_from_returns(returns)
    )


def maximum_drawdown_from_prices(
    prices: NDArray[np.float64],
) -> float:
    """
    Compute the maximum drawdown from a price series.
    """

    return maximum_drawdown_from_drawdown(
        drawdown_from_prices(prices)
    )


def maximum_drawdown(
    history: PriceHistory,
) -> float:
    """
    Compute the maximum drawdown from a PriceHistory.
    """

    return maximum_drawdown_from_drawdown(
        drawdown(history)
    )


def maximum_drawdown_asset(
    asset: Asset,
    registry: DataRegistry,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> float:
    """
    Compute the maximum drawdown directly from an asset.
    """

    end = end or date.today()
    start = start or end - timedelta(days=365)

    history = registry.history(
        asset,
        start=start,
        end=end,
        interval=interval,
    )

    return maximum_drawdown(history)


def portfolio_drawdown(
    portfolio_data: PortfolioData,
) -> NDArray[np.float64]:
    """
    Compute the drawdown series of a portfolio.
    """

    return drawdown_from_prices(
        portfolio_data.value,
    )


def portfolio_maximum_drawdown(
    portfolio_data: PortfolioData,
) -> float:
    """
    Compute the maximum drawdown of a portfolio.
    """

    return maximum_drawdown_from_drawdown(
        portfolio_drawdown(portfolio_data)
    )

