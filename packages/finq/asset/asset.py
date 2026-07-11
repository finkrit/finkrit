# finkrit/packages/finq/asset/asset.py
from dataclasses import dataclass

from packages.finq.datatype import AssetType, Currency, Exchange


@dataclass(frozen=True, slots=True)
class Asset:

    ticker: str
    asset_type: AssetType
    currency: Currency
    exchange: Exchange

    