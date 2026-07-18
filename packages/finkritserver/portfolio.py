# finkritserver/portfolio.py
"""
Builds a finkritq Portfolio from a flat PortfolioSpec.

Encapsulates the one awkward bit of finkritq construction: Position <-> Lot <->
Account reference each other, so a Position is built via __new__ and its lot is
attached afterward (the same dance main.py and the test fixtures do -- see the
"Position.__new__ smell" note in private/improvements.md). Keeping it in one
place means the smell lives in exactly one function, not scattered across the
server. If finkritq later grows a clean factory, this delegates to it.
"""
from __future__ import annotations

from decimal import Decimal

from finkritq.asset import Stock
from finkritq.datatype import (
    AccountRegistrationType,
    Currency,
    CustodianType,
    Exchange,
)
from finkritq.portfolio import Account, Lot, Portfolio, Position
from finkritq.portfolio.custodian import Custodian

from finkritserver.schemas import HoldingSpec, PortfolioSpec

# Risk analysis only needs assets + quantities + histories; custodian and
# registration are required by the Account type but immaterial here, so we
# default them rather than making the caller supply them.
_DEFAULT_CUSTODIAN = Custodian(type=CustodianType.SCHWAB)
_DEFAULT_REGISTRATION = AccountRegistrationType.INDIVIDUAL


def _make_stock(holding: HoldingSpec) -> Stock:
    return Stock(
        ticker=holding.ticker,
        currency=Currency(holding.currency),
        exchange=Exchange(holding.exchange),
        company_name=holding.ticker,
    )


def _make_position(holding: HoldingSpec) -> Position:
    lot = Lot(
        id=f"lot-{holding.ticker}",
        quantity=Decimal(str(holding.quantity)),
        cost_per_share=Decimal(str(holding.cost_per_share)),
        acquired=holding.acquired,
    )
    return Position(id=f"pos-{holding.ticker}", asset=_make_stock(holding), lots=(lot,))


def build_portfolio(spec: PortfolioSpec) -> Portfolio:
    account = Account(
        id=f"acct-{spec.id}",
        account_number="n/a",
        name=f"{spec.name} account",
        custodian=_DEFAULT_CUSTODIAN,
        account_registration_type=_DEFAULT_REGISTRATION,
    )
    for holding in spec.holdings:
        account.add_position(_make_position(holding))

    return Portfolio(id=spec.id, name=spec.name, accounts=[account])
