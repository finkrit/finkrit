# finagent/assistant.py

from __future__ import annotations

from datetime import date

from pydantic_ai import models

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.data.providers import MemoizingHistoryProvider, YFinanceProvider
from finkritq.datatype import MarketIndex
from finkritq.portfolio import Portfolio

from finagent.agent.risk import RiskAgent
from finagent.deps import AgentDeps
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.store import InMemoryStore, Store


class Assistant:
    """
    Seamless entrypoint. Two surfaces mirroring the two ways to use the stack:

        assistant = Assistant(model="anthropic:claude-sonnet-5")
        assistant.register_portfolio(portfolio)

        assistant.ask("What's my portfolio's volatility?")   # conversational (LLM)
        assistant.risk.report("port-1", assistant.deps)       # typed, deterministic

    Today `ask` routes to the risk specialist directly. When more specialists
    exist (optimization, ...) this becomes an orchestrator that delegates.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str,
        store: Store | None = None,
        registry: DataRegistry | None = None,
    ) -> None:
        self._store = store or InMemoryStore()
        self._registry = registry or _default_registry()
        self._store.register_asset(MarketIndex.SP500.as_asset())

        self.risk = RiskAgent(model=model)

    @property
    def deps(self) -> AgentDeps:
        return AgentDeps(store=self._store, registry=self._registry)

    def register_portfolio(self, portfolio: Portfolio) -> None:
        self._store.register_portfolio(portfolio)

    def register_asset(self, asset: Asset) -> None:
        self._store.register_asset(asset)

    def ask(self, question: str) -> str:
        # Sync convenience for scripts/notebooks. Single specialist today;
        # becomes delegation across specialists later.
        return self.risk.ask(question, self.deps)

    async def ask_async(self, question: str) -> str:
        # Async path for the web server. Same routing as ask().
        return await self.risk.ask_async(question, self.deps)

    def report(
        self,
        portfolio_id: str,
        metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
    ) -> PortfolioRiskReport:
        return self.risk.report(portfolio_id, self.deps, metrics)


def _default_registry() -> DataRegistry:
    registry = DataRegistry()
    # Session-scoped memoization so repeated questions about the same holdings
    # don't re-download. Persistent caching is a later (v2) layer.
    provider = MemoizingHistoryProvider(YFinanceProvider())
    registry.register_history(provider)
    registry.register_snapshot(YFinanceProvider())
    return registry

