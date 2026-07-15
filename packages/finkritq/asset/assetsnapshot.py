# finkrit/packages/finkritq/asset/assetsnapshot.py
from datetime import datetime

from dataclasses import dataclass

from finkritq.asset import Asset


@dataclass(frozen=True, slots=True)
class AssetSnapshot:
    asset: Asset

    last_price: float
    previous_close: float

    timestamp: datetime | None = None