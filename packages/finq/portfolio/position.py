# finkrit/packages/finq/portfolio/position.py
from dataclasses import dataclass

from packages.finq.asset.asset import Asset


@dataclass(frozen=True)
class Position:
    asset: Asset
    quantity: float
    average_cost: float | None = None
    

    