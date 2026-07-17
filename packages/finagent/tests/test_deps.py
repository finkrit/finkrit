# finagent/tests/test_deps.py
"""
Direct tests for AgentDeps -- previously had no test file at all. Note it is
NOT frozen (unlike every other dataclass in this package: ToolContract,
ToolBinding, Capability, the RiskReport family are all frozen=True). These
tests document current (mutable) behavior; whether that's intentional is a
separate design question, not something a test alone answers.
"""
from __future__ import annotations

from finagent.deps import AgentDeps
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_registry


class TestAgentDeps:

    def test_construction_exposes_store_and_registry(self):
        store = InMemoryStore()
        registry = make_registry()
        deps = AgentDeps(store=store, registry=registry)
        assert deps.store is store
        assert deps.registry is registry

    def test_currently_mutable_unlike_the_rest_of_the_package(self):
        # Documents actual behavior -- flip this to pytest.raises(FrozenInstanceError)
        # if/when AgentDeps is made frozen to match the rest of the codebase.
        deps = AgentDeps(store=InMemoryStore(), registry=make_registry())
        replacement = InMemoryStore()
        deps.store = replacement
        assert deps.store is replacement
