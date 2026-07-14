# finkrit/tests/fixtures.py
"""
Shared test fixtures — deterministic, no network calls.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np

from packages.finkritq.asset import Stock
from packages.finkritq.datatype import (
    AccountRegistrationType,
    Currency,
    CustodianType,
    Exchange,
    PriceHistory,
)
from packages.finkritq.portfolio import Account, Lot, Portfolio, Position
from packages.finkritq.portfolio.custodian import Custodian


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


def make_custodian() -> Custodian:
    return Custodian(type=CustodianType.SCHWAB)


def make_account(
    account_id: str = "acct-1",
    account_number: str = "1234",
    name: str = "Test Account",
) -> Account:
    return Account(
        id=account_id,
        account_number=account_number,
        name=name,
        custodian=make_custodian(),
        account_registration_type=AccountRegistrationType.INDIVIDUAL,
    )


def make_position(
    stock: Stock,
    account: Account | None = None,
    quantity: Decimal = Decimal("10"),
    cost: Decimal = Decimal("100"),
    position_id: str = "pos-1",
    lot_id: str = "lot-1",
    acquired: date = LONG_TERM_DATE,
) -> Position:
    """
    Build a properly wired Position + Lot pair.
    Uses a sentinel lot to satisfy Lot.__post_init__, then replaces
    the lot's position reference via slots-compatible assignment.
    """
    if account is None:
        account = make_account()

    # 1. Build position with a placeholder lots tuple (will be replaced)
    pos = Position.__new__(Position)
    pos.id = position_id
    pos.account = account
    pos.asset = stock
    pos.notes = None
    pos.last_price = None

    # 2. Build the lot pointing at the real position
    lot = Lot(
        id=lot_id,
        position=pos,
        quantity=quantity,
        cost_per_share=cost,
        acquired=acquired,
    )
    pos.lots = (lot,)
    return pos


def make_two_stock_portfolio() -> tuple[Portfolio, Stock, Stock]:
    a = make_stock("AAA")
    b = make_stock("BBB")
    account = make_account()
    pos_a = make_position(a, account=account, quantity=Decimal("10"), cost=Decimal("100"), position_id="pos-a", lot_id="lot-a")
    pos_b = make_position(b, account=account, quantity=Decimal("5"),  cost=Decimal("200"), position_id="pos-b", lot_id="lot-b")
    account.positions = [pos_a, pos_b]
    portfolio = Portfolio(id="port-1", name="Test Portfolio", accounts=[account])
    return portfolio, a, b
