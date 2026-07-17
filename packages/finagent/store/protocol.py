# finagent/store/protocol.py

from __future__ import annotations

from typing import Protocol

from finkritq.asset import Asset
from finkritq.portfolio import Portfolio


class Store(Protocol):
    """
    Resolves the ids/tickers an LLM can supply back into the domain
    objects finkritintel bindings actually operate on.
    """

    def get_portfolio(self, portfolio_id: str) -> Portfolio: ...

    def register_portfolio(self, portfolio: Portfolio) -> None: ...

    def get_asset(self, ticker: str) -> Asset: ...

    def register_asset(self, asset: Asset) -> None: ...
