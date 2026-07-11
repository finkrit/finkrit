from abc import ABC, abstractmethod

from packages.finq.asset import Asset
from packages.finq.asset import AssetSnapshot


class SnapshotProvider(ABC):

    @abstractmethod
    def snapshot(self, asset: Asset) -> AssetSnapshot:
        """Return the latest market snapshot for an asset."""
        ...