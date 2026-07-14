# finkrit/tests/packages/finq/portfolio/conftest.py
"""
Shared pytest fixtures for portfolio tests.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from packages.finq.asset import Stock
from packages.finq.datatype import AccountRegistrationType, Currency, CustodianType, Exchange
from packages.finq.portfolio import Account, Lot, Portfolio, Position
from packages.finq.portfolio.custodian import Custodian
from tests.fixtures import (
    LONG_TERM_DATE,
    SHORT_TERM_DATE,
    make_account,
    make_custodian,
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
def custodian():
    return make_custodian()


@pytest.fixture
def account(custodian):
    return Account(
        id="acct-1",
        account_number="1234",
        name="Test Account",
        custodian=custodian,
        account_registration_type=AccountRegistrationType.INDIVIDUAL,
    )


@pytest.fixture
def position(account, stock_a):
    return make_position(stock_a, account=account)


@pytest.fixture
def lot(position):
    return Lot(
        id="lot-1",
        position=position,
        quantity=Decimal("10"),
        cost_per_share=Decimal("100"),
        acquired=LONG_TERM_DATE,
    )


@pytest.fixture
def two_stock_portfolio(stock_a, stock_b):
    account = make_account()
    pos_a = make_position(stock_a, account=account, quantity=Decimal("10"), cost=Decimal("100"), position_id="pos-a", lot_id="lot-a")
    pos_b = make_position(stock_b, account=account, quantity=Decimal("5"),  cost=Decimal("200"), position_id="pos-b", lot_id="lot-b")
    account.positions = [pos_a, pos_b]
    return Portfolio(id="port-1", name="Test Portfolio", accounts=[account])


@pytest.fixture
def position_a(account, stock_a):
    return make_position(stock_a, account=account, position_id="pos-a", lot_id="lot-a")


@pytest.fixture
def position_b(account, stock_b):
    return make_position(stock_b, account=account, position_id="pos-b", lot_id="lot-b")
