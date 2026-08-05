# finkritcore/tests/store/test_memory.py
from __future__ import annotations

import pytest

from finkritcore.store import AssetNotFoundError, InMemoryStore, PortfolioNotFoundError
from finkritcore.tests.fixtures import make_portfolio, make_stock


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


class TestNotFoundMessages:
    """A miss is read by a model, not a person, and it reads the message as a
    statement about the portfolio. One was observed passing a SQL query where a
    ticker belonged, getting back "no asset registered with ticker ...", and
    telling the user their portfolio was empty underneath a beta it had just
    computed from twelve holdings."""

    def _asset_error(self, store: InMemoryStore, ticker: str) -> str:
        with pytest.raises(AssetNotFoundError) as raised:
            store.get_asset(ticker)
        return str(raised.value)

    def test_a_missing_ticker_names_the_ones_that_exist(self):
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        message = self._asset_error(store, "MISSING")
        assert "AAA" in message and "BBB" in message

    def test_an_invented_argument_is_not_echoed_whole(self):
        # The observed one was a full query. Repeating it buries the list of
        # real tickers that follows, which is the recoverable half.
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        message = self._asset_error(store, "+SELECT tickers FROM plus.portfolio WHERE id = 1")
        assert "…" in message
        assert "AAA" in message

    def test_only_a_genuinely_empty_store_reads_as_empty(self):
        assert "none are registered" in self._asset_error(InMemoryStore(), "AAA")

    def test_a_populated_store_never_reads_as_empty(self):
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        assert "none are registered" not in self._asset_error(store, "MISSING")

    def test_a_missing_portfolio_names_the_ones_that_exist(self):
        store = InMemoryStore()
        store.register_portfolio(make_portfolio("port-1"))
        with pytest.raises(PortfolioNotFoundError) as raised:
            store.get_portfolio("missing")
        assert "port-1" in str(raised.value)

    def test_a_long_list_is_capped_and_says_so(self):
        store = InMemoryStore()
        for n in range(60):
            store.register_asset(make_stock(f"T{n:03d}"))
        message = self._asset_error(store, "MISSING")
        assert "20 more" in message
