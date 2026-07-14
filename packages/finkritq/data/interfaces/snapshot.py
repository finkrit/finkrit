# finkrit/packages/finkritq/data/interfaces/snapshot.py
from abc import ABC, abstractmethod

from packages.finkritq.asset import Asset
from packages.finkritq.asset import AssetSnapshot


class SnapshotProvider(ABC):

    @abstractmethod
    def snapshot(self, asset: Asset) -> AssetSnapshot:
        """Return the latest market snapshot for an asset."""
        ...