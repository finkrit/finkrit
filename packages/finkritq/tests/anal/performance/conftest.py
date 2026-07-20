# finkrit/packages/finkritq/tests/anal/performance/conftest.py
"""
Shared fixtures for the performance test sub-suite. Deterministic, no network.
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.portfolio import PortfolioData
from finkritq.tests.fixtures import make_price_history, make_two_stock_portfolio


@pytest.fixture
def two_stock_portfolio_data() -> PortfolioData:
    # Two stocks, 60 trading days, seeded so both bases drift apart measurably.
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
