# finagent/store/memory.py

from __future__ import annotations

from dataclasses import dataclass, field

from finkritq.asset import Asset
from finkritq.portfolio import Portfolio


class PortfolioNotFoundError(KeyError):
    pass


class AssetNotFoundError(KeyError):
    pass


@dataclass(slots=True)
class InMemoryStore:
    """
    Default Store: no persistence across processes. Registering a
    portfolio also registers its holdings, so tickers already in a
    portfolio resolve without a separate register_asset call.
    """

    _portfolios: dict[str, Portfolio] = field(default_factory=dict)
    _assets: dict[str, Asset] = field(default_factory=dict)

    def register_portfolio(self, portfolio: Portfolio) -> None:
        self._portfolios[portfolio.id] = portfolio
        for asset in portfolio.assets:
            self.register_asset(asset)

    def get_portfolio(self, portfolio_id: str) -> Portfolio:
        try:
            return self._portfolios[portfolio_id]
        except KeyError:
            raise PortfolioNotFoundError(
                f"No portfolio registered with id '{portfolio_id}'."
            ) from None

    def register_asset(self, asset: Asset) -> None:
        self._assets[asset.ticker] = asset

    def get_asset(self, ticker: str) -> Asset:
        try:
            return self._assets[ticker]
        except KeyError:
            raise AssetNotFoundError(
                f"No asset registered with ticker '{ticker}'."
            ) from None
