# finkrit/packages/finkritq/tests/portfolio/conftest.py
"""
Shared pytest fixtures for portfolio tests.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from finkritq.portfolio import Portfolio, TaxLot
from finkritq.tests.fixtures import (
    LONG_TERM_DATE,
    make_position,
    make_stock,
    make_two_stock_portfolio,
)


@pytest.fixture
def stock_a():
    return make_stock("AAA")


@pytest.fixture
def stock_b():
    return make_stock("BBB")


@pytest.fixture
def asset(stock_a):
    return stock_a


@pytest.fixture
def position(stock_a):
    return make_position(stock_a)


@pytest.fixture
def taxlot():
    return TaxLot(
        id="lot-1",
        quantity=Decimal("10"),
        cost_per_share=Decimal("100"),
        acquired=LONG_TERM_DATE,
    )


@pytest.fixture
def two_stock_portfolio(stock_a, stock_b):
    pos_a = make_position(stock_a, quantity=Decimal("10"), cost=Decimal("100"), position_id="pos-a", lot_id="lot-a")
    pos_b = make_position(stock_b, quantity=Decimal("5"),  cost=Decimal("200"), position_id="pos-b", lot_id="lot-b")
    return Portfolio(id="port-1", name="Test Portfolio", positions=[pos_a, pos_b])


@pytest.fixture
def position_a(stock_a):
    return make_position(stock_a, position_id="pos-a", lot_id="lot-a")


@pytest.fixture
def position_b(stock_b):
    return make_position(stock_b, position_id="pos-b", lot_id="lot-b")
