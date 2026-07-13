# finkrit/tests/packages/finq/anal/risk/conftest.py
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
    RETURNS_A,
    RETURNS_B,
    PRICES,
)

# ---------------------------------------------------------------------------
# PortfolioData fixture — 60 trading days, two stocks, no network calls
# ---------------------------------------------------------------------------

@pytest.fixture
def two_stock_portfolio_data() -> PortfolioData:
    portfolio, a, b = make_two_stock_portfolio()
    rng = np.random.default_rng(7)
    close_a = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.010, 60))), 4)
    close_b = np.round(200.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, 60))), 4)
    return PortfolioData(
        portfolio=portfolio,
        _histories={
            a: make_price_history(close_a),
            b: make_price_history(close_b),
        },
    )
