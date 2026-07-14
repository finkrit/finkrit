# finkrit/packages/finkritq/data/interfaces/__init__.py
from .history import HistoryProvider
from .snapshot import SnapshotProvider

__all__ = ["HistoryProvider", "SnapshotProvider"]