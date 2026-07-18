# finagent/store/protocol.py

from __future__ import annotations

from typing import Protocol

from finkritq.asset import Asset
from finkritq.portfolio import Portfolio

# The id used when a caller doesn't specify one -- the product is currently
# scoped to a single portfolio (no multi-portfolio UX), so both the server's
# registration endpoint and the risk agent's chat instructions default to
# this rather than requiring the user/frontend to invent and track an id.
# The Store itself still supports arbitrary ids for a future multi-portfolio
# product; this is a convention layered on top, not a Store limitation.
DEFAULT_PORTFOLIO_ID = "primary"


class Store(Protocol):
    """
    Resolves the ids/tickers an LLM can supply back into the domain
    objects finkritintel bindings actually operate on.
    """

    def get_portfolio(self, portfolio_id: str) -> Portfolio: ...

    def register_portfolio(self, portfolio: Portfolio) -> None: ...

    def list_portfolios(self) -> list[Portfolio]: ...

    def get_asset(self, ticker: str) -> Asset: ...

    def register_asset(self, asset: Asset) -> None: ...

    def list_assets(self) -> list[Asset]: ...
