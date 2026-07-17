# finagent/tests/adapter/test_resolve.py
from __future__ import annotations

import pytest
from pydantic_ai import ModelRetry

from finagent.adapter.resolve import FIELD_RESOLVERS, INJECTED_FIELDS, resolve_field
from finagent.deps import AgentDeps
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry, make_stock


class TestFieldResolvers:

    def test_portfolio_resolver_resolves_by_id(self):
        store = InMemoryStore()
        portfolio = make_portfolio()
        store.register_portfolio(portfolio)
        deps = AgentDeps(store=store, registry=make_registry())

        resolved = resolve_field(FIELD_RESOLVERS["portfolio"], deps, "port-1")
        assert resolved is portfolio

    def test_asset_resolver_resolves_by_ticker(self):
        store = InMemoryStore()
        stock = make_stock("AAPL")
        store.register_asset(stock)
        deps = AgentDeps(store=store, registry=make_registry())

        resolved = resolve_field(FIELD_RESOLVERS["asset"], deps, "AAPL")
        assert resolved is stock

    def test_benchmark_history_or_asset_resolver_shares_asset_resolution(self):
        assert (
            FIELD_RESOLVERS["benchmark_history_or_asset"].resolve
            is FIELD_RESOLVERS["asset"].resolve
        )

    def test_unknown_portfolio_raises_model_retry(self):
        deps = AgentDeps(store=InMemoryStore(), registry=make_registry())
        with pytest.raises(ModelRetry):
            resolve_field(FIELD_RESOLVERS["portfolio"], deps, "missing")

    def test_unknown_asset_raises_model_retry(self):
        deps = AgentDeps(store=InMemoryStore(), registry=make_registry())
        with pytest.raises(ModelRetry):
            resolve_field(FIELD_RESOLVERS["asset"], deps, "MISSING")

    def test_registry_is_injected_not_resolved(self):
        assert "registry" in INJECTED_FIELDS
        assert "registry" not in FIELD_RESOLVERS
