# finkrit/packages/finkritq/optimize/expected_returns.py
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.datatype import ReturnCalculationMethod
from finkritq.portfolio import PortfolioData


def expected_returns_from_returns(
    returns: NDArray[np.float64],
    annualized: bool = True,
    periods_per_year: int = 252,
) -> NDArray[np.float64]:
    """
    Expected (mean) return per asset from a return matrix.

    Parameters
    ----------
    returns
        Array of shape (n_assets, n_periods).

    Uses the ARITHMETIC mean, not the geometric (CAGR): mean-variance
    optimization pairs expected return with variance, and both must be arithmetic
    for wᵀμ and wᵀΣw to describe the same distribution. (The geometric mean lives
    in the performance layer as annualized_return, for reporting realized growth.)
    Annualizing scales the per-period mean by periods_per_year, matching how
    covariance_matrix annualizes, so μ and Σ share the same time base.
    """
    mean_per_period = np.mean(returns, axis=1)
    if annualized:
        return mean_per_period * periods_per_year
    return mean_per_period


def expected_returns(
    portfolio_data: PortfolioData,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> NDArray[np.float64]:
    """
    Expected return vector for a portfolio's assets, aligned to
    ``portfolio_data.assets``.

    Uses SIMPLE returns to match covariance_matrix (portfolio aggregation is only
    exact for simple returns), so μ and Σ are computed on the same series.
    """
    returns = portfolio_data.return_matrix(ReturnCalculationMethod.SIMPLE)
    return expected_returns_from_returns(
        returns,
        annualized=annualized,
        periods_per_year=periods_per_year,
    )
