from dataclasses import dataclass
from datetime import date

from packages.finq.asset import Asset


@dataclass(frozen=True, slots=True)
class Lot:
    """
    A tax lot representing shares acquired together at the same cost basis.
    """

    asset: Asset
    quantity: float
    cost: float
    acquired: date

    