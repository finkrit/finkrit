# finkrit/packages/finkritq/asset/asset.py
from dataclasses import dataclass, field

from finkritq.datatype import AssetType, Currency, Exchange


@dataclass(frozen=True, slots=True)
class Asset:
    """
    An asset's *identity* is its ticker + exchange. The remaining fields are
    descriptive, not identifying, so they are excluded from equality/hashing
    (``compare=False``). This matters because assets are used as dict keys
    everywhere (PortfolioData histories, the store, snapshot maps): without
    this, two references to "AAPL" that differ only in a display field (e.g.
    company_name) would be unequal and silently miss on lookup.

    ``exchange`` is optional: market indices (e.g. ^GSPC) are not listed on an
    exchange, so they legitimately have none.
    """

    ticker: str
    asset_type: AssetType = field(compare=False)
    currency: Currency = field(compare=False)
    exchange: Exchange | None  # required, but may be None for non-listed assets (indices)

    