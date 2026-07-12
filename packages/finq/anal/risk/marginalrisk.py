# finkrit/packages/finq/anal/risk/marginalrisk.py

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.risk.covariance import covariance_matrix
from packages.finq.anal.risk.volatility import portfolio_volatility
from packages.finq.portfolio import PortfolioData


def marginal_contribution_to_risk(portfolio_data: PortfolioData) -> NDArray[np.float64]:
    """
    Compute the marginal contribution to portfolio risk (MCTR).

    Returns
    -------
    ndarray
        Marginal contribution to risk for each asset.
    """

    covariance = covariance_matrix(portfolio_data)
    weights = portfolio_data.weights
    volatility = portfolio_volatility(portfolio_data)

    if volatility == 0.0:
        raise ValueError("Portfolio volatility is zero.")
    return covariance @ weights/volatility

