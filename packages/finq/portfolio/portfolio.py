# finkrit/packages/finq/portfolio/portfolio.py
from typing import List
import numpy as np

from packages.finq.portfolio.position import Position


class Portfolio:

    def __init__(self, positions: List[Position]):
        self._positions = positions

    @property
    def positions(self):
        return tuple(self._positions)

    @property
    def assets(self):
        return [p.asset for p in self._positions]

    @property
    def quantities(self):
        return np.array([p.quantity for p in self._positions])
    
    """
    we expect portfolio to be created once during session
    in case of update we will create the portfolio again
    """
    def add_position(self, asset, quantity):
        self._positions.append(Position(asset=asset, quantity=quantity))

