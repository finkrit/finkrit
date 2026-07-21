# finagent/tests/fixtures.py
"""
Fixtures for finagent tests. No network: a deterministic fake
HistoryProvider stands in for YFinanceProvider.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np

from finkritq.asset import Asset, Stock
from finkritq.data import DataRegistry
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import (
    Currency,
    Exchange,
    PriceHistory,
)
from finkritq.portfolio import Portfolio, Position, TaxLot

_DATES = np.array(
    [np.datetime64("2024-01-02", "D") + np.timedelta64(i, "D") for i in range(30)],
    dtype="datetime64[D]",
).astype("datetime64[ns]")


class FakeHistoryProvider(HistoryProvider):
    """Deterministic price series, seeded per-ticker -- no network."""

    def history(self, asset: Asset, start=None, end=None, interval: str = "1d") -> PriceHistory:
        rng = np.random.default_rng(abs(hash(asset.ticker)) % (2**32))
        closes = 100.0 + np.cumsum(rng.normal(0, 1, len(_DATES)))
        return PriceHistory(
            dates=_DATES,
            open=closes,
            high=closes,
            low=closes,
            close=closes,
            volume=np.ones(len(_DATES), dtype=np.int64),
        )


def make_registry() -> DataRegistry:
    registry = DataRegistry()
    registry.register_history(FakeHistoryProvider())
    return registry


def make_stock(ticker: str) -> Stock:
    return Stock(ticker=ticker, currency=Currency.USD, exchange=Exchange.NASDAQ, company_name=f"{ticker} Corp")


def _make_position(stock: Stock, quantity: str, position_id: str, lot_id: str) -> Position:
    lot = TaxLot(id=lot_id, quantity=Decimal(quantity), cost_per_share=Decimal("100"), acquired=date(2024, 1, 1))
    return Position(id=position_id, asset=stock, lots=(lot,))


def make_portfolio(portfolio_id: str = "port-1") -> Portfolio:
    """Two-stock portfolio -- single-asset portfolios degenerate in finkritq's covariance math."""
    stock_a = make_stock("AAA")
    stock_b = make_stock("BBB")

    return Portfolio(
        id=portfolio_id,
        name="Test Portfolio",
        positions=[
            _make_position(stock_a, "10", "pos-a", "lot-a"),
            _make_position(stock_b, "5", "pos-b", "lot-b"),
        ],
    )
