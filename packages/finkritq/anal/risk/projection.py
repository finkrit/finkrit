# finkrit/packages/finkritq/anal/risk/projection.py
"""
Forward return range: a projection of where a portfolio's return could land over
a horizon, the interval to compare against an owner's comfort band.

Two estimation methods, chosen by the caller (the same VaREstimationMethod the
VaR estimators use):

    PARAMETRIC   assume returns are roughly normal: mu_h plus or minus z sigma_h.
                 Smooth and easy to present, but thin-tailed versus reality.
    HISTORICAL   take the empirical quantiles of the actual return distribution,
                 so fat tails survive, scaled to the horizon by root-time.

Both center on the same drift (mu_h) and differ only in how they spread. The
drift defaults to the portfolio's historical annualized return and can be
overridden (pass 0.0 for a drift-free risk band). Volatility and the empirical
distribution both come from the portfolio's own ex-ante (constant-mix) returns.
This is a planning band, not a guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm

from finkritq.anal.risk.volatility import portfolio_volatility
from finkritq.datatype import VaREstimationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class ForwardRange:
    """
    A projected return interval over ``horizon_days``.

    ``low`` and ``high`` bound the central ``confidence`` mass (0.95 leaves 2.5%
    in each tail). ``expected_return`` and ``volatility`` are the annualized
    inputs used, kept for transparency, ``method`` records how the spread was
    estimated.
    """

    low: float
    high: float
    horizon_days: int
    confidence: float
    expected_return: float
    volatility: float
    method: VaREstimationMethod


def _annualized_return_from_value(
    value: NDArray[np.float64],
    periods_per_year: int,
) -> float:
    # Geometric annualized return of the value path, computed here (rather than
    # importing the performance layer) so the risk package stays free of a
    # risk-to-performance dependency.
    n = len(value) - 1
    if n <= 0 or value[0] <= 0.0:
        return 0.0
    return float((value[-1] / value[0]) ** (periods_per_year / n) - 1.0)


def forward_return_range(
    portfolio_data: PortfolioData,
    horizon_days: int = 126,
    confidence: float = 0.95,
    method: VaREstimationMethod = VaREstimationMethod.PARAMETRIC,
    expected_return: float | None = None,
    periods_per_year: int = 252,
) -> ForwardRange:
    """
    Central return interval over ``horizon_days`` at ``confidence``.

    ``horizon_days`` is in trading days (126 is about six months). Both methods
    center on the horizon drift ``mu_h`` (compounded from the annualized mean).
    PARAMETRIC spreads by ``z * sigma_h`` (sigma root-time scaled), HISTORICAL
    spreads by the empirical per-period quantile deviations, also root-time
    scaled. ``expected_return`` (annualized) overrides the drift, pass 0.0 for a
    drift-free band.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1.")
    if method is VaREstimationMethod.MONTE_CARLO:
        raise ValueError("forward_return_range supports PARAMETRIC and HISTORICAL only.")

    if expected_return is None:
        mu_annual = _annualized_return_from_value(portfolio_data.value, periods_per_year)
    else:
        mu_annual = expected_return

    # frac * periods_per_year == horizon_days, so the horizon holds this many
    # return periods, and root-time scaling uses sqrt(horizon_days).
    fraction = horizon_days / periods_per_year
    mu_h = (1.0 + mu_annual) ** fraction - 1.0
    root_time = np.sqrt(horizon_days)

    if method is VaREstimationMethod.PARAMETRIC:
        sigma_annual = portfolio_volatility(
            portfolio_data,
            basis=WeightingBasis.CONSTANT_MIX,
            annualized=True,
            periods_per_year=periods_per_year,
        )
        sigma_h = sigma_annual * np.sqrt(fraction)
        z = float(norm.ppf(0.5 * (1.0 + confidence)))
        low, high = mu_h - z * sigma_h, mu_h + z * sigma_h
    else:  # HISTORICAL
        returns = portfolio_data.constant_mix_returns()
        mean = float(np.mean(returns))
        lower_q = float(np.quantile(returns, 0.5 * (1.0 - confidence)))
        upper_q = float(np.quantile(returns, 0.5 * (1.0 + confidence)))
        # Per-period quantile deviations from the mean, root-time scaled onto the
        # horizon and re-centered on mu_h. Volatility reported for transparency.
        low = mu_h + (lower_q - mean) * root_time
        high = mu_h + (upper_q - mean) * root_time
        sigma_annual = float(np.std(returns, ddof=1)) * np.sqrt(periods_per_year)

    return ForwardRange(
        low=low,
        high=high,
        horizon_days=horizon_days,
        confidence=confidence,
        expected_return=mu_annual,
        volatility=sigma_annual,
        method=method,
    )
