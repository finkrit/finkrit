# finkritserver/portfolio.py
"""
Builds a finkritq Portfolio from a flat PortfolioSpec.

finq's Portfolio is a lean set of Positions (no accounts, custodian, or tax-org
structure), so this is a straight construction: each holding becomes a Position
holding a single TaxLot. The ownership/legal graph (accounts, registration,
custodian) belongs to the RIA layer, not to risk/performance analysis.
"""
from __future__ import annotations

from decimal import Decimal

from finkritq.asset import Stock
from finkritq.datatype import Currency, Exchange
from finkritq.portfolio import Portfolio, Position, TaxLot

from finkritserver.schemas import HoldingSpec, PortfolioSpec


def _make_stock(holding: HoldingSpec) -> Stock:
    return Stock(
        ticker=holding.ticker,
        currency=Currency(holding.currency),
        exchange=Exchange(holding.exchange),
        company_name=holding.ticker,
    )


def _make_position(holding: HoldingSpec) -> Position:
    lot = TaxLot(
        id=f"lot-{holding.ticker}",
        quantity=Decimal(str(holding.quantity)),
        cost_per_share=Decimal(str(holding.cost_per_share)),
        acquired=holding.acquired,
    )
    return Position(id=f"pos-{holding.ticker}", asset=_make_stock(holding), lots=(lot,))


def build_portfolio(spec: PortfolioSpec) -> Portfolio:
    return Portfolio(
        id=spec.id,
        name=spec.name,
        positions=[_make_position(holding) for holding in spec.holdings],
    )
