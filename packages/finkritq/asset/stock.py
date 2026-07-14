# finkrit/packages/finkritq/asset/stock.py
from dataclasses import dataclass, field

from packages.finkritq.asset.asset import Asset
from packages.finkritq.datatype import AssetType

@dataclass(frozen=True, slots=True)
class Stock(Asset):
    company_name: str

    asset_type: AssetType = field(
        default=AssetType.STOCK,
        init=False,
    )

