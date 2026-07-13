# finkrit/tests/fixtures.py
"""
Shared test fixtures — deterministic, no network calls.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from packages.finq.asset import Stock
from packages.finq.asset.lot import Lot
from packages.finq.datatype import Currency, Exchange, PriceHistory
from packages.finq.portfolio import Portfolio, Position


# ---------------------------------------------------------------------------
# Price helpers
# ---------------------------------------------------------------------------

def make_dates(n: int, start: str = "2024-01-02") -> np.ndarray:
    base = np.datetime64(start, "D")
    return np.array([base + np.timedelta64(i, "D") for i in range(n)], dtype="datetime64[D]")


def make_price_history(
    close: list[float] | np.ndarray,
    start: str = "2024-01-02",
) -> PriceHistory:
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    dates = make_dates(n, start)
    return PriceHistory(
        dates=dates,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=np.ones(n, dtype=np.int64),
    )


# Flat prices → zero returns (useful for edge-case tests)
FLAT_PRICES = [100.0] * 10
# Linearly rising prices
RISING_PRICES = [100.0 + i for i in range(10)]
# Prices that reproduce known β = 1  (asset == benchmark)
MARKET_PRICES = [100.0, 101.0, 99.0, 102.0, 98.0, 103.0, 97.0, 104.0, 96.0, 105.0]


# ---------------------------------------------------------------------------
# Asset / Portfolio helpers
# ---------------------------------------------------------------------------

def make_stock(ticker: str = "TST") -> Stock:
    return Stock(
        ticker=ticker,
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name=f"{ticker} Corp",
    )


def make_position(stock: Stock, quantity: float = 10.0, cost: float = 100.0) -> Position:
    lot = Lot(
        asset=stock,
        quantity=quantity,
        cost_per_share=cost,
        acquired=date(2024, 1, 2),
    )
    return Position(asset=stock, lots=(lot,))


def make_two_stock_portfolio() -> tuple[Portfolio, Stock, Stock]:
    a = make_stock("AAA")
    b = make_stock("BBB")
    portfolio = Portfolio([
        make_position(a, quantity=10, cost=100),
        make_position(b, quantity=5, cost=200),
    ])
    return portfolio, a, b
