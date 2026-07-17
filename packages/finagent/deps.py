# finagent/deps.py

from __future__ import annotations

from dataclasses import dataclass

from finkritq.data import DataRegistry
from finagent.store import Store


@dataclass(slots=True)
class AgentDeps:
    store: Store
    registry: DataRegistry
