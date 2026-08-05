# finkritcore/store/memory.py

from __future__ import annotations

from dataclasses import dataclass, field

from finkritq.asset import Asset
from finkritq.portfolio import Portfolio


class PortfolioNotFoundError(KeyError):
    pass


class AssetNotFoundError(KeyError):
    pass


# How many names to list when a lookup misses. Enough to be the whole answer
# for an ordinary portfolio, short enough that a large one does not turn a tool
# error into a wall the model has to read past.
_NAMES_IN_ERROR = 40

# A miss usually means the model invented the argument, and an invented one can
# be arbitrarily long. One local model passed an entire SQL query where a
# ticker belonged. Echoing that whole buries the useful half of the message.
_ECHO_WIDTH = 40


def _echo(value: str) -> str:
    flat = " ".join(str(value).split())
    if len(flat) > _ECHO_WIDTH:
        flat = flat[: _ECHO_WIDTH - 1] + "…"
    return f"'{flat}'"


def _not_found(kind: str, asked: str, known: list[str]) -> str:
    """The message a model reads after asking for something that is not here.

    It names what is registered, not only what is missing. A bare "no asset
    with ticker X" is true of the argument but reads as a claim about the
    portfolio, and a model with no way to enumerate its holdings will believe
    it: one was observed telling the user their portfolio was empty, directly
    underneath a beta it had just computed from twelve holdings. Listing the
    real names turns a dead end into a correction the model can act on, and
    makes the empty case the only one that reads as empty.
    """
    if not known:
        return f"No {kind} registered as {asked}, and none are registered at all."
    shown = ", ".join(sorted(known)[:_NAMES_IN_ERROR])
    rest = len(known) - _NAMES_IN_ERROR
    more = f", and {rest} more" if rest > 0 else ""
    return (
        f"No {kind} registered as {asked}. The registered ones are: "
        f"{shown}{more}. Use one of those exactly as written."
    )


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
                _not_found("portfolio", _echo(portfolio_id), list(self._portfolios))
            ) from None

    def list_portfolios(self) -> list[Portfolio]:
        return list(self._portfolios.values())

    def register_asset(self, asset: Asset) -> None:
        self._assets[asset.ticker] = asset

    def get_asset(self, ticker: str) -> Asset:
        try:
            return self._assets[ticker]
        except KeyError:
            raise AssetNotFoundError(
                _not_found("asset", _echo(ticker), list(self._assets))
            ) from None

    def list_assets(self) -> list[Asset]:
        return list(self._assets.values())
