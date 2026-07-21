# finkrit/packages/finkritq/anal/performance/flows.py
"""
Returns in the presence of external cash flows, the two standard flow-aware measures,
time-weighted and money-weighted (IRR).

The moment a portfolio takes contributions or withdrawals, a naive
end/start - 1 is wrong: the value moved for reasons that are not investment
performance. The two honest answers measure different things:

    * Time-weighted (TWR): strips the flows out and chains the per-period returns,
so it reflects the *manager's* decisions independent of when the client added
or removed money. This is the GIPS/advisor-skill number.

    * Money-weighted (MWR / IRR): the internal rate of return of the actual dated
cash flows, so it reflects the *client's* realized dollar experience,
including the timing of their flows.

Both take the actual observed value path plus a per-period external-flow series
(see datatype.CashFlow / flows_to_series). Sign: a flow > 0 is a contribution.
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def time_weighted_return(
    values: NDArray[np.float64],
    flows: NDArray[np.float64],
    annualized: bool = False,
    periods_per_year: int = 252,
) -> float:
    """
    Time-weighted return over the value path, stripping external flows.

    Each period's return removes that period's flow before comparing to the prior
    value: r_t = (V_t - CF_t) / V_{t-1} - 1. The sub-period returns are chained.
    ``values`` is the actual observed portfolio value at each date (not the
    current-composition series), ``flows`` is aligned to it, flow at t occurring at
    observation t (flows[0] is ignored, V_0 is the starting stake).
    """
    values = np.asarray(values, dtype=np.float64)
    flows = np.asarray(flows, dtype=np.float64)
    if len(values) < 2:
        return 0.0

    prior = values[:-1]
    later = values[1:]
    period_flows = flows[1:]
    period_returns = (later - period_flows) / prior - 1.0
    twr = float(np.prod(1.0 + period_returns) - 1.0)

    if annualized:
        n_periods = len(values) - 1
        return (1.0 + twr) ** (periods_per_year / n_periods) - 1.0
    return twr


def _irr(cashflows: NDArray[np.float64], lo: float = -0.999999, hi: float = 10.0,
         tol: float = 1e-10, max_iter: int = 200) -> float:
    # Per-period internal rate of return: the r solving sum CF_t/(1+r)^t = 0,
    # by bisection (no scipy dependency). Returns nan if the flows do not bracket
    # a root (e.g. all same sign).
    powers = np.arange(len(cashflows))

    # Clamp the bracket so (1+r)^n stays inside float range across the series
    # length: too close to -1 underflows (1+r)^n to 0 -> inf/nan in the divide,
    # too large overflows it. Without this, long daily series break the solver.
    n = max(len(cashflows) - 1, 1)
    span = 250.0 / n
    lo = max(lo, -1.0 + 10.0 ** (-span))
    hi = min(hi, -1.0 + 10.0 ** span)

    def npv(rate: float) -> float:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            return float(np.sum(cashflows / (1.0 + rate) ** powers))

    f_lo, f_hi = npv(lo), npv(hi)
    if not np.isfinite(f_lo) or not np.isfinite(f_hi) or f_lo * f_hi > 0:
        return float("nan")

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = npv(mid)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def money_weighted_return(
    values: NDArray[np.float64],
    flows: NDArray[np.float64],
    annualized: bool = False,
    periods_per_year: int = 252,
) -> float:
    """
    Money-weighted return (IRR) of the actual dated cash flows.

    The investor's cash flows are: pay in the starting value at t0, pay in
    contributions (receive withdrawals) as they occur, and receive the final value
    at the end. The per-period IRR solves NPV = 0, annualizing compounds it by
    periods_per_year. Returns nan if the flows do not bracket a rate.
    """
    values = np.asarray(values, dtype=np.float64)
    flows = np.asarray(flows, dtype=np.float64)
    if len(values) < 2:
        return 0.0

    # Investor perspective: contributions are outflows (negative), the starting
    # value is the initial investment, the final value is returned at the end.
    cashflows = -flows.copy()
    cashflows[0] -= values[0]
    cashflows[-1] += values[-1]

    rate = _irr(cashflows)
    if np.isnan(rate):
        return rate
    if annualized:
        return (1.0 + rate) ** periods_per_year - 1.0
    return rate
