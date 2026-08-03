# finagent/assistant.py

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from pydantic_ai import models

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.data.providers import (
    MemoizingHistoryProvider,
    MemoizingSnapshotProvider,
    YFinanceProvider,
)
from finkritq.datatype import MarketIndex
from finkritq.portfolio import Portfolio

from finkritintel.integration.finkritq import PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING

from finagent.agent.optimization import OptimizationAgent
from finagent.agent.orchestrator import Orchestrator
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.agent.tax import TaxAgent
from finagent.conversation import DEFAULT_MAX_TURNS, Conversation
from finagent.deps import AgentDeps
from finagent.ingest import ParsedPortfolio, parse_portfolio_csv, parse_portfolio_csv_async
from finagent.logging_model import wrap_model_for_logging
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.report.tax_signals import TaxSignalsReport, compose_tax_signals
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
        event_handler=None,
    ) -> None:
        # model is optional, a dashboard-only user can construct an Assistant
        # and call .report()/.risk.report() with no LLM and no API key. .ask()
        # raises a clear error if no model was configured (F-1).
        self._store = store or InMemoryStore()
        self._registry = registry or _default_registry()
        self._store.register_asset(MarketIndex.SP500.as_asset())
        # Optional live step callback (pydantic-ai event_stream_handler), carried
        # into deps so it reaches the orchestrator and every nested specialist.
        self._event_handler = event_handler

        # Wrap once so every agent and the CSV-parse call log their LLM requests
        # when FINKRIT_LOG_LLM is set (a no-op otherwise, and None stays None).
        model = wrap_model_for_logging(model)
        self._model = model
        self.risk = RiskAgent(model=model)
        self.performance = PerformanceAgent(model=model)
        self.optimization = OptimizationAgent(model=model)
        self.tax = TaxAgent(model=model)
        self._specialists = {
            "risk": self.risk,
            "performance": self.performance,
            "optimization": self.optimization,
            "tax": self.tax,
        }
        self.orchestrator = Orchestrator(
            model, self.risk, self.performance, self.optimization, self.tax,
        )

    @property
    def deps(self) -> AgentDeps:
        return AgentDeps(store=self._store, registry=self._registry, event_handler=self._event_handler)

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

    def conversation(self, agent: str | None = None, max_turns: int = DEFAULT_MAX_TURNS) -> Conversation:
        """
        A threaded, multi-turn exchange that remembers what came before, so
        follow-up questions work.

            chat = assistant.conversation()          # orchestrator, all domains
            chat.ask("what is my volatility?")
            chat.ask("and how does that compare to my drawdown?")

        With no `agent` this threads the orchestrator, which is the right default
        for open-ended chat. Naming a specialist (risk, performance,
        optimization, tax) threads that one directly, cheaper when the domain is
        known. `deps` is passed as a callable so the conversation always sees the
        current store and registry.
        """
        runner = self.orchestrator if agent is None else self._specialists[agent]
        return Conversation(runner, lambda: self.deps, max_turns=max_turns)

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

    def tax_signals(self, portfolio_id: str, **kwargs) -> TaxSignalsReport:
        # Deterministic, no LLM: the dashboard's actionable tax view (harvest
        # candidates, wash sale warnings, long term countdowns). kwargs pass
        # through to compose_tax_signals (rates, thresholds, as_of).
        portfolio = self._store.get_portfolio(portfolio_id)
        return compose_tax_signals(portfolio, self._registry, **kwargs)

    def prefetch_events(self, portfolio_id: str):
        """
        Warm the data caches for one portfolio, yielding a progress event per
        ticker as its download lands. Deterministic, no LLM.

        Downloads run in parallel (one worker per ticker) and each event is
        emitted on completion, so a consumer can render a live progress bar.
        Warms exactly what the dashboard endpoints read: the default-window
        price history (same memoizer key) and the spot snapshot (TTL cache),
        plus the S&P 500 benchmark the risk report betas against. A ticker
        that fails reports status "error" with the reason and does not stop
        the rest, mirroring the partial-success rule reports follow.

        The portfolio lookup happens eagerly (a miss raises before any event),
        the download fan-out lazily on iteration.
        """
        portfolio = self._store.get_portfolio(portfolio_id)
        assets = [position.asset for position in portfolio.positions]
        assets.append(MarketIndex.SP500.as_asset())

        registry = self._registry

        def events():
            yield {"event": "start", "tickers": [asset.ticker for asset in assets]}

            def warm(asset: Asset) -> None:
                registry.history(asset)
                try:
                    registry.snapshot(asset)
                except RuntimeError:
                    # No snapshot provider registered (offline registry): the
                    # tax tools fall back to history, already warmed above.
                    pass

            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(warm, asset): asset for asset in assets}
                for future in as_completed(futures):
                    asset = futures[future]
                    try:
                        future.result()
                        yield {"ticker": asset.ticker, "status": "ready"}
                    except Exception as exc:  # noqa: BLE001 - reported, not raised
                        yield {"ticker": asset.ticker, "status": "error", "detail": str(exc)}

            yield {"event": "end"}

        return events()

    def rebalance_compare(self, portfolio_id: str, **kwargs) -> dict:
        # Deterministic, no LLM: the same fixed strategy menu the chat compare
        # tool runs (full, band_edge, partial_fill), served straight to the
        # dashboard through the identical intel binding so the two surfaces can
        # never disagree on a number. kwargs pass through to the binding
        # (objective, gain_budget, tolerance, method, as_of).
        portfolio = self._store.get_portfolio(portfolio_id)
        return PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING.execute(
            portfolio=portfolio, registry=self._registry, **kwargs
        )

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
    # don't re-download. Persistent caching is a later (v2) layer. Snapshots
    # get a short TTL cache so a prefetch pass and the view reads that follow
    # it share one quote per ticker instead of hitting the network twice.
    provider = MemoizingHistoryProvider(YFinanceProvider())
    registry.register_history(provider)
    registry.register_snapshot(MemoizingSnapshotProvider(YFinanceProvider()))
    return registry

