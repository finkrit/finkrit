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


# ---------------------------------------------------------------------------
# Deterministic price series (seeded — no randomness between runs)
# ---------------------------------------------------------------------------

# ~60 trading days of realistic prices starting at 100
_rng = np.random.default_rng(42)
_log_returns_60 = _rng.normal(0.0004, 0.012, 60)
MARKET_PRICES: np.ndarray = np.round(
    100.0 * np.exp(np.cumsum(np.insert(_log_returns_60, 0, 0.0))), 4
)  # shape (61,)

# Flat prices → zero returns (edge-case tests)
FLAT_PRICES: np.ndarray = np.full(60, 100.0, dtype=np.float64)

# Linearly rising prices (monotone, no drawdown)
RISING_PRICES: np.ndarray = 100.0 + np.arange(60, dtype=np.float64)

# Falling-then-recovering series for drawdown tests
_mid = 60 // 2
PEAK_FALL_PRICES: np.ndarray = np.concatenate([
    np.linspace(100.0, 80.0, _mid),   # fall 20 %
    np.linspace(80.0, 95.0, 60 - _mid),  # partial recovery
])

# ---------------------------------------------------------------------------
# Shared return arrays (used across analytics tests)
# ---------------------------------------------------------------------------

# 60 deterministic daily returns
RETURNS_A: np.ndarray = np.diff(np.log(MARKET_PRICES))          # shape (60,)
# β of RETURNS_B vs RETURNS_A ≈ 1.5
RETURNS_B: np.ndarray = RETURNS_A * 1.5

# Convenience alias used by some tests
PRICES: np.ndarray = MARKET_PRICES

# ---------------------------------------------------------------------------
# Date constants for long-term / short-term lot tests
# ---------------------------------------------------------------------------

LONG_TERM_DATE  = date(2020, 1, 1)   # well over 365 days ago
SHORT_TERM_DATE = date.today()        # acquired today → 0 days


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
