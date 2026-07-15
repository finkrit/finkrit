# finkrit/packages/finkritq/data/interfaces/snapshot.py
from abc import ABC, abstractmethod

from finkritq.asset import Asset
from finkritq.asset import AssetSnapshot


class SnapshotProvider(ABC):

    @abstractmethod
    def snapshot(self, asset: Asset) -> AssetSnapshot:
        """Return the latest market snapshot for an asset."""
        ...