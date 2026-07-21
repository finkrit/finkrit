# finkrit/packages/finkritq/datatype/cashflow.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class CashFlow:
    """
    An external cash flow into or out of a portfolio on a date.

    Sign convention (portfolio's point of view): ``amount > 0`` is a contribution
    (money in), ``amount < 0`` is a withdrawal (money out). External flows are the
    thing that makes a naive return wrong, they change the portfolio's value
    without being investment performance, which is exactly why time-weighted and
    money-weighted returns exist to handle them (see performance.flows).
    """

    date: date_type
    amount: float


def flows_to_series(
    cashflows: list[CashFlow],
    dates: NDArray[np.datetime64],
) -> NDArray[np.float64]:
    """
    Collapse dated cash flows onto a per-period array aligned to ``dates`` (a
    portfolio value series' observation dates), summing any flows that land on the
    same date. Flows dated outside the window are ignored. The result[t] is the net
    external flow occurring at observation t, ready to feed the TWR/MWR functions.
    """
    day_index = {np.datetime64(day, "D"): i for i, day in enumerate(dates)}
    series = np.zeros(len(dates), dtype=np.float64)
    for flow in cashflows:
        key = np.datetime64(flow.date, "D")
        index = day_index.get(key)
        if index is not None:
            series[index] += flow.amount
    return series

