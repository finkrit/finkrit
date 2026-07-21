# finkrit/packages/finkritq/tests/policy/conftest.py
"""
Fixtures for the policy sub-suite. Deterministic, no network.

`weighted_portfolio` uses flat prices so market-value weights equal a known
split exactly (compliance tests need exact weights). `varying_portfolio` uses a
seeded series so it has real volatility (suitability / projection need it).
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_price_history, make_position, make_stock


def _flat_history(price: float = 100.0, n: int = 40):
    return make_price_history(np.full(n, price))


@pytest.fixture
def weighted_portfolio():
    # Flat prices, so weights equal the quantity split exactly: AAA 50%, BBB 30%,
    # CCC 20%. Returns the data and the three assets for building policies.
    a, b, c = make_stock("AAA"), make_stock("BBB"), make_stock("CCC")
    positions = [
        make_position(a, quantity=Decimal("50"), position_id="p-a", lot_id="l-a"),
        make_position(b, quantity=Decimal("30"), position_id="p-b", lot_id="l-b"),
        make_position(c, quantity=Decimal("20"), position_id="p-c", lot_id="l-c"),
    ]
    portfolio = Portfolio(id="m", name="Policy Test", positions=positions)
    histories = {a: _flat_history(), b: _flat_history(), c: _flat_history()}
    return PortfolioData(portfolio=portfolio, _histories=histories), (a, b, c)


@pytest.fixture
def varying_portfolio() -> PortfolioData:
    a, b = make_stock("AAA"), make_stock("BBB")
    rng = np.random.default_rng(3)
    close_a = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.011, 90))), 4)
    close_b = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.013, 90))), 4)
    positions = [
        make_position(a, quantity=Decimal("50"), position_id="p-a", lot_id="l-a"),
        make_position(b, quantity=Decimal("50"), position_id="p-b", lot_id="l-b"),
    ]
    portfolio = Portfolio(id="v", name="Varying", positions=positions)
    histories = {a: make_price_history(close_a), b: make_price_history(close_b)}
    return PortfolioData(portfolio=portfolio, _histories=histories)
