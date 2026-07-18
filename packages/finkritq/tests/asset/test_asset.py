# finkritq/tests/asset/test_asset_identity.py
"""
Asset identity (D-C, D-D): identity is ticker + exchange; descriptive fields
(company_name, currency, asset_type) don't affect equality/hashing. Assets are
used as dict keys throughout, so this prevents silent lookup misses.
"""
from __future__ import annotations

from finkritq.asset import Stock
from finkritq.datatype import Currency, Exchange, MarketIndex


def _stock(ticker="AAPL", company_name="Apple Inc.", exchange=Exchange.NASDAQ, currency=Currency.USD):
    return Stock(ticker=ticker, currency=currency, exchange=exchange, company_name=company_name)


class TestAssetIdentity:

    def test_same_ticker_and_exchange_are_equal_despite_display_fields(self):
        assert _stock(company_name="Apple Inc.") == _stock(company_name="Apple")

    def test_equal_assets_hash_equal(self):
        assert hash(_stock(company_name="Apple Inc.")) == hash(_stock(company_name="Apple"))

    def test_usable_as_dict_key_across_display_spellings(self):
        histories = {_stock(company_name="Apple Inc."): "data"}
        assert histories[_stock(company_name="Apple")] == "data"

    def test_different_exchange_is_a_different_asset(self):
        assert _stock(exchange=Exchange.NASDAQ) != _stock(exchange=Exchange.NYSE)

    def test_different_ticker_is_a_different_asset(self):
        assert _stock(ticker="AAPL") != _stock(ticker="MSFT")

    def test_currency_is_not_part_of_identity(self):
        assert _stock(currency=Currency.USD) == _stock(currency=Currency.EUR)


class TestOptionalExchange:
    """D-D: indices are not exchange-listed; exchange=None is valid and typed."""

    def test_market_index_as_asset_has_no_exchange(self):
        sp500 = MarketIndex.SP500.as_asset()
        assert sp500.exchange is None
        assert sp500.ticker == "^GSPC"

    def test_two_indices_are_distinguished_by_ticker(self):
        assert MarketIndex.SP500.as_asset() != MarketIndex.NASDAQ.as_asset()

    def test_index_usable_as_dict_key(self):
        sp = MarketIndex.SP500.as_asset()
        assert {sp: 1}[MarketIndex.SP500.as_asset()] == 1
