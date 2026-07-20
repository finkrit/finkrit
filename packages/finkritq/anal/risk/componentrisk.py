# finkrit/packages/finkritq/anal/risk/componentrisk.py

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk.marginalrisk import (marginal_contribution_to_risk)
from finkritq.portfolio import PortfolioData


def component_contribution_to_risk(
    portfolio_data: PortfolioData,
) -> NDArray[np.float64]:
    """
    Compute the component contribution to portfolio risk (CCTR).

    Basis: CONSTANT_MIX only (weights * MCTR). Like MCTR it has no buy-and-hold
    analogue and takes no `basis` argument. The components sum to the CONSTANT_MIX
    portfolio volatility.

    Returns
    -------
    ndarray
        Component contribution to risk for each asset.
    """

    return portfolio_data.weight_vector * marginal_contribution_to_risk(portfolio_data)