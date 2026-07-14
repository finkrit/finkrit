# finkrit/packages/finkritq/analytics/returns.py
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from packages.finkritq.datatype import ReturnCalculationMethod


def calculate_returns(
    prices: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> NDArray[np.float64]:
    """
    Calculate periodic returns from a price history.

    Parameters
    ----------
    history : nd array of prices
    method : ReturnCalculationMethod
        Return calculation method.

    Returns
    -------
    NDArray[np.float64]
        Periodic returns.
    """


    if method == ReturnCalculationMethod.LOG:
        return np.diff(np.log(prices))

    if method == ReturnCalculationMethod.SIMPLE:
        return (prices[1:] / prices[:-1]) - 1

    raise ValueError(f"Unsupported return calculation method: {method}")

