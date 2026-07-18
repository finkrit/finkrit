# finagent/store/__init__.py
"""
finagent.store — id/ticker -> domain-object resolution.

Because an LLM (and a programmatic caller) references things by id or ticker,
something has to turn ``"port-1"`` back into a ``Portfolio`` and ``"AAPL"``
into an ``Asset``. That is the ``Store``.

  - ``protocol`` — the ``Store`` Protocol: ``get_portfolio`` / ``get_asset``
    plus ``register_*``. This is the important seam: when the service
    needs real persistence (surviving process restarts, sharing state between
    a scheduled job and an interactive session), it implements ``Store``
    against a real backend and passes it to ``Assistant(store=...)`` —
    finagent never needs to know that implementation exists.

  - ``memory`` — ``InMemoryStore``, the default. Zero cross-process
    persistence by design (persistence is a service concern). It exists so
    ids resolve to real objects *within one process*. Registering a portfolio
    auto-registers its holdings by ticker, so a portfolio's own assets resolve
    without extra calls. Misses raise ``PortfolioNotFoundError`` /
    ``AssetNotFoundError`` (``KeyError`` subclasses), which the adapter layer
    turns into a recoverable ``ModelRetry``.

  - ``DEFAULT_PORTFOLIO_ID`` — the id used when the product is scoped to a
    single portfolio (no id the user/frontend has to invent or track). Both
    finkritserver's registration default and the risk agent's chat
    instructions use this same constant.
"""

from .memory import AssetNotFoundError, InMemoryStore, PortfolioNotFoundError
from .protocol import DEFAULT_PORTFOLIO_ID, Store

__all__ = [
    "Store",
    "InMemoryStore",
    "PortfolioNotFoundError",
    "AssetNotFoundError",
    "DEFAULT_PORTFOLIO_ID",
]
