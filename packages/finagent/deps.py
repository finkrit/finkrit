# finagent/deps.py

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from finkritq.data import DataRegistry
from finagent.store import Store


@dataclass(slots=True)
class AgentDeps:
    store: Store
    registry: DataRegistry
    # Optional pydantic-ai event_stream_handler. Carried in deps so it threads
    # through the orchestrator down into every nested specialist run (deps flow
    # down). None means no live step output, the default for tests and servers.
    event_handler: Callable | None = None
