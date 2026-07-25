# finkrit/packages/finkritq/anal/risk/marginalrisk.py

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.covariance import covariance_matrix
from finkritq.anal.risk.volatility import portfolio_volatility
from finkritq.portfolio import PortfolioData


def marginal_contribution_to_risk(portfolio_data: PortfolioData) -> NDArray[np.float64]:
    """
    Compute the marginal contribution to portfolio risk (MCTR).

    Basis: CONSTANT_MIX only. MCTR lives in covariance space (Σ, w) and has no
    buy-and-hold analogue, unlike the dual metrics it takes no `basis`
    argument. See WeightingBasis.

    Returns
    -------
    ndarray
        Marginal contribution to risk for each asset.
    """

    covariance = covariance_matrix(portfolio_data)
    weights = portfolio_data.weight_vector
    volatility = portfolio_volatility(portfolio_data)

    # A NaN volatility must be rejected explicitly, NaN == 0.0 is False so the
    # zero guard alone would let a NaN divisor through and return an all-NaN
    # vector, which serializes to null for every holding.
    if not np.isfinite(volatility) or volatility == 0.0:
        raise ValueError(
            f"Portfolio volatility is {volatility}, cannot compute marginal "
            f"contribution to risk. The window likely has too few or degenerate "
            f"observations."
        )
    return (covariance @ weights) / volatility

