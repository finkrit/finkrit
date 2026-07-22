# finagent/assistant.py

from __future__ import annotations

from datetime import date

from pydantic_ai import models

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.data.providers import MemoizingHistoryProvider, YFinanceProvider
from finkritq.datatype import MarketIndex
from finkritq.portfolio import Portfolio

from finagent.agent.optimization import OptimizationAgent
from finagent.agent.orchestrator import Orchestrator
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.deps import AgentDeps
from finagent.ingest import ParsedPortfolio, parse_portfolio_csv, parse_portfolio_csv_async
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.store import InMemoryStore, Store


class Assistant:
    """
    Seamless entrypoint. Two surfaces mirroring the two ways to use the stack:

        assistant = Assistant(model="anthropic:claude-sonnet-5")
        assistant.register_portfolio(portfolio)

        assistant.ask("What's my portfolio's volatility?")   # risk specialist (default)
        assistant.ask("...", agent="optimization")            # a named specialist
        assistant.route("Review my portfolio")                # orchestrator, fans out
        assistant.risk.report("port-1", assistant.deps)       # typed, deterministic

    Holds the three specialists (risk, performance, optimization) plus an
    orchestrator. `ask` targets one specialist directly (default risk, no routing
    overhead), `route` delegates through the orchestrator, which can call several
    specialists and combine them.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        store: Store | None = None,
        registry: DataRegistry | None = None,
    ) -> None:
        # model is optional, a dashboard-only user can construct an Assistant
        # and call .report()/.risk.report() with no LLM and no API key. .ask()
        # raises a clear error if no model was configured (F-1).
        self._store = store or InMemoryStore()
        self._registry = registry or _default_registry()
        self._store.register_asset(MarketIndex.SP500.as_asset())

        self._model = model
        self.risk = RiskAgent(model=model)
        self.performance = PerformanceAgent(model=model)
        self.optimization = OptimizationAgent(model=model)
        self._specialists = {
            "risk": self.risk,
            "performance": self.performance,
            "optimization": self.optimization,
        }
        self.orchestrator = Orchestrator(model, self.risk, self.performance, self.optimization)

    @property
    def deps(self) -> AgentDeps:
        return AgentDeps(store=self._store, registry=self._registry)

    def register_portfolio(self, portfolio: Portfolio) -> None:
        self._store.register_portfolio(portfolio)

    def list_portfolios(self) -> list[Portfolio]:
        return self._store.list_portfolios()

    def register_asset(self, asset: Asset) -> None:
        self._store.register_asset(asset)

    def ask(self, question: str, agent: str = "risk") -> str:
        # Direct to one specialist (default risk), no orchestration overhead.
        return self._specialists[agent].ask(question, self.deps)

    async def ask_async(self, question: str, agent: str = "risk") -> str:
        return await self._specialists[agent].ask_async(question, self.deps)

    def route(self, question: str) -> str:
        # The all-encompassing path: the orchestrator picks specialist(s) and
        # combines them. Costs an extra orchestration loop, see Orchestrator.
        return self.orchestrator.ask(question, self.deps)

    async def route_async(self, question: str) -> str:
        return await self.orchestrator.ask_async(question, self.deps)

    def report(
        self,
        portfolio_id: str,
        metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
    ) -> PortfolioRiskReport:
        return self.risk.report(portfolio_id, self.deps, metrics)

    def _require_model(self) -> models.Model | models.KnownModelName | str:
        if self._model is None:
            raise RuntimeError(
                "This Assistant has no model configured, parsing a portfolio "
                "upload requires one (it's an LLM extraction, not deterministic)."
            )
        return self._model

    def parse_portfolio_csv(self, csv_text: str) -> ParsedPortfolio:
        # Sync convenience for scripts/notebooks. Does NOT register anything,
        # the caller reviews/corrects the result, then register_portfolio()s it.
        return parse_portfolio_csv(csv_text, self._require_model())

    async def parse_portfolio_csv_async(self, csv_text: str) -> ParsedPortfolio:
        # Async path for the web server's upload endpoint.
        return await parse_portfolio_csv_async(csv_text, self._require_model())


def _default_registry() -> DataRegistry:
    registry = DataRegistry()
    # Session-scoped memoization so repeated questions about the same holdings
    # don't re-download. Persistent caching is a later (v2) layer.
    provider = MemoizingHistoryProvider(YFinanceProvider())
    registry.register_history(provider)
    registry.register_snapshot(YFinanceProvider())
    return registry

