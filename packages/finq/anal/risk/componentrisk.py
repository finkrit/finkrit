# finkrit/packages/finq/anal/risk/componentrisk.py

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from packages.finq.anal.risk.marginalrisk import (marginal_contribution_to_risk)
from packages.finq.portfolio import PortfolioData


def component_contribution_to_risk(
    portfolio_data: PortfolioData,
) -> NDArray[np.float64]:
    """
    Compute the component contribution to portfolio risk (CCTR).

    Returns
    -------
    ndarray
        Component contribution to risk for each asset.
    """

    return (portfolio_data.weights * marginal_contribution_to_risk(portfolio_data))