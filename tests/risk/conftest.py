# finkrit/tests/risk/conftest.py
"""
Shared pytest fixtures for the risk test sub-suite.
All fixtures are deterministic — no network calls.
"""
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.portfolio import PortfolioData
from tests.fixtures import (
    make_price_history,
    make_two_stock_portfolio,
    MARKET_PRICES,
)

# ---------------------------------------------------------------------------
# Return arrays used across multiple test modules
# ---------------------------------------------------------------------------

RETURNS_A = np.array(
    [0.01, -0.02, 0.03, -0.01, 0.02, 0.00, -0.03, 0.01, 0.02, -0.01],
    dtype=np.float64,
)
# β of RETURNS_B vs RETURNS_A should be ≈ 1.5
RETURNS_B = RETURNS_A * 1.5

PRICES = np.array(MARKET_PRICES, dtype=np.float64)


# ---------------------------------------------------------------------------
# PortfolioData fixture (two stocks, no network)
# ---------------------------------------------------------------------------

@pytest.fixture
def two_stock_portfolio_data() -> PortfolioData:
    portfolio, a, b = make_two_stock_portfolio()
    close_a = np.array([100.0, 102.0, 101.0, 103.0, 105.0,
                        104.0, 106.0, 108.0, 107.0, 109.0], dtype=np.float64)
    close_b = np.array([200.0, 198.0, 201.0, 199.0, 203.0,
                        202.0, 205.0, 204.0, 207.0, 206.0], dtype=np.float64)
    return PortfolioData(
        portfolio=portfolio,
        _histories={
            a: make_price_history(close_a),
            b: make_price_history(close_b),
        },
    )
