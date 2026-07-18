# finkrit/packages/finkritq/asset/stock.py
from dataclasses import dataclass, field

from finkritq.asset.asset import Asset
from finkritq.datatype import AssetType

@dataclass(frozen=True, slots=True)
class Stock(Asset):
    # company_name is descriptive, not part of identity (a field re-declared in
    # a subclass gets a fresh field(), so the base's compare=False is not
    # inherited -- both the override and company_name set it explicitly).
    company_name: str = field(compare=False)

    asset_type: AssetType = field(
        default=AssetType.STOCK,
        init=False,
        compare=False,
    )

