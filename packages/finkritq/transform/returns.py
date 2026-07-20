# finkrit/packages/finkritq/transform/returns.py
"""
The returns transform: turn a series of levels (prices, or any wealth path) into
a series of period-over-period returns.

This is neither a datatype (it is behavior, not a value) nor an analytic (it is
the input measures are computed from, not a measure). It is a foundational
numeric transform, so it lives in its own low-level module that everything else
can depend on downward. `ReturnCalculationMethod` is co-located here because it
parameterizes this transform, which also keeps this module free of any finkrit
imports and so free of dependency cycles.
"""
from __future__ import annotations

from enum import Enum

import numpy as np
from numpy.typing import NDArray


class ReturnCalculationMethod(Enum):
    SIMPLE = "simple"
    LOG = "log"


def periodic_returns(
    levels: NDArray[np.float64],
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
) -> NDArray[np.float64]:
    """
    Compute period-over-period returns from a level series.

    A "level series" is anything that moves up and down over time and whose
    ratios are meaningful, e.g. a close-price series or a portfolio value path.
    The output has one fewer element than the input (the first period has no
    prior level to compare against).

    LOG
        ln(level_t / level_t-1). Log returns add across time.
    SIMPLE
        level_t / level_t-1 minus 1. Simple returns compound multiplicatively.
    """

    if method == ReturnCalculationMethod.LOG:
        return np.diff(np.log(levels))

    if method == ReturnCalculationMethod.SIMPLE:
        return (levels[1:] / levels[:-1]) - 1

    raise ValueError(f"Unsupported return calculation method: {method}")
