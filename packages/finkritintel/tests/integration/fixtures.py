# finkritintel/tests/integration/fixtures.py
"""
Fixtures for finkritintel integration tests.

Builds minimal deterministic PortfolioData objects — no network, no registry.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np

from finkritq.asset import Stock
from finkritq.datatype import (
    Currency,
    Exchange,
    PriceHistory,
)
from finkritq.portfolio import Account, Lot, Portfolio, Position
from finkritq.portfolio.custodian import Custodian
from finkritq.datatype import AccountRegistrationType, CustodianType
from finkritq.portfolio import PortfolioData


# ---------------------------------------------------------------------------
# Price series — seeded, deterministic
# ---------------------------------------------------------------------------

_rng = np.random.default_rng(0)
_log_returns = _rng.normal(0.0004, 0.012, 60)
_prices_a = np.round(100.0 * np.exp(np.cumsum(np.insert(_log_returns, 0, 0.0))), 4)  # (61,)
_prices_b = np.round(120.0 * np.exp(np.cumsum(np.insert(_log_returns * 1.5, 0, 0.0))), 4)

_dates = np.array(
    [np.datetime64("2024-01-02", "D") + np.timedelta64(i, "D") for i in range(61)],
    dtype="datetime64[D]",
)

BENCHMARK_HISTORY = PriceHistory(
    dates=_dates,
    open=_prices_a,
    high=_prices_a,
    low=_prices_a,
    close=_prices_a,
    volume=np.ones(61, dtype=np.int64),
)


def _make_history(prices: np.ndarray) -> PriceHistory:
    return PriceHistory(
        dates=_dates,
        open=prices,
        high=prices,
        low=prices,
        close=prices,
        volume=np.ones(len(prices), dtype=np.int64),
    )


def _make_stock(ticker: str) -> Stock:
    return Stock(
        ticker=ticker,
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name=f"{ticker} Corp",
    )


def _make_position(stock: Stock, account: Account, quantity: str, position_id: str, lot_id: str) -> Position:
    lot = Lot(
        id=lot_id,
        quantity=Decimal(quantity),
        cost_per_share=Decimal("100"),
        acquired=date(2020, 1, 1),
    )
    return Position(id=position_id, asset=stock, lots=(lot,))


def make_portfolio_data() -> PortfolioData:
    """Two-stock portfolio with 61 days of aligned price history."""
    stock_a = _make_stock("AAA")
    stock_b = _make_stock("BBB")

    custodian = Custodian(type=CustodianType.SCHWAB)
    account = Account(
        id="acct-1",
        account_number="1234",
        name="Test Account",
        custodian=custodian,
        account_registration_type=AccountRegistrationType.INDIVIDUAL,
    )

    pos_a = _make_position(stock_a, account, "10", "pos-a", "lot-a")
    pos_b = _make_position(stock_b, account, "5", "pos-b", "lot-b")
    account.positions = [pos_a, pos_b]

    portfolio = Portfolio(id="port-1", name="Test Portfolio", accounts=[account])

    return PortfolioData(
        portfolio=portfolio,
        _histories={
            stock_a: _make_history(_prices_a),
            stock_b: _make_history(_prices_b),
        },
    )

