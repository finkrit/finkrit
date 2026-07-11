from datetime import datetime

from dataclasses import dataclass

from packages.finq.asset import Asset


@dataclass(frozen=True, slots=True)
class AssetSnapshot:
    asset: Asset

    last_price: float
    previous_close: float

    timestamp: datetime | None = None