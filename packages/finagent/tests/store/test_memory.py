# finagent/tests/store/test_memory.py
from __future__ import annotations

import pytest

from finagent.store import AssetNotFoundError, InMemoryStore, PortfolioNotFoundError
from finagent.tests.fixtures import make_portfolio, make_stock


class TestInMemoryStore:

    def test_register_and_get_portfolio(self):
        store = InMemoryStore()
        portfolio = make_portfolio()
        store.register_portfolio(portfolio)
        assert store.get_portfolio("port-1") is portfolio

    def test_get_unknown_portfolio_raises(self):
        store = InMemoryStore()
        with pytest.raises(PortfolioNotFoundError):
            store.get_portfolio("missing")

    def test_register_portfolio_auto_registers_holdings(self):
        store = InMemoryStore()
        portfolio = make_portfolio()
        store.register_portfolio(portfolio)
        assert store.get_asset("AAA").ticker == "AAA"
        assert store.get_asset("BBB").ticker == "BBB"

    def test_register_and_get_asset(self):
        store = InMemoryStore()
        stock = make_stock("MSFT")
        store.register_asset(stock)
        assert store.get_asset("MSFT") is stock

    def test_get_unknown_asset_raises(self):
        store = InMemoryStore()
        with pytest.raises(AssetNotFoundError):
            store.get_asset("MISSING")

    # --- F-3: enumeration for the dashboard's portfolio selector ---

    def test_list_portfolios_empty_by_default(self):
        assert InMemoryStore().list_portfolios() == []

    def test_list_portfolios_returns_registered(self):
        store = InMemoryStore()
        p1, p2 = make_portfolio("port-1"), make_portfolio("port-2")
        store.register_portfolio(p1)
        store.register_portfolio(p2)
        listed = store.list_portfolios()
        assert len(listed) == 2
        assert p1 in listed and p2 in listed

    def test_list_assets_includes_auto_registered_holdings(self):
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        tickers = {a.ticker for a in store.list_assets()}
        assert {"AAA", "BBB"} <= tickers
