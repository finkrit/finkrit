# finagent/assistant.py

from __future__ import annotations

from pydantic_ai import models

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.portfolio import Portfolio

from finagent.agent.base import DEFAULT_LANGUAGE
from finagent.agent.optimization import OptimizationAgent
from finagent.agent.orchestrator import Orchestrator
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.agent.tax import TaxAgent
from finagent.conversation import DEFAULT_MAX_TURNS, Conversation
from finagent.deps import AgentDeps
from finagent.ingest import (
    DEFAULT_PORTFOLIO_NAME,
    ParsedPortfolio,
    parse_portfolio_csv,
    parse_portfolio_csv_async,
)
from finagent.logging_model import wrap_model_for_logging
from finkritcore.report.metric import RiskMetric
from finkritcore.report.report import PortfolioRiskReport
from finkritcore.report.tax_signals import TaxSignalsReport
from finkritcore.desk import Desk
from finkritcore.store import Store


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

    The deterministic surface is not implemented here. It lives on ``self.desk``,
    a ``finkritcore.Desk``, and the methods below delegate to it. An
    integrator who wants the analytics without an agent framework builds that     desk directly and reads identical numbers from the same store.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        store: Store | None = None,
        registry: DataRegistry | None = None,
        event_handler=None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        # model is optional, a dashboard-only user can construct an Assistant
        # and call .report()/.risk.report() with no LLM and no API key. .ask()
        # raises a clear error if no model was configured (F-1).
        self.desk = Desk(store=store, registry=registry)
        # The agents resolve against the desk's own store and registry, not
        # copies, so the chat surface and the dashboard read one state.
        self._store = self.desk.store
        self._registry = self.desk.registry
        # Optional live step callback (pydantic-ai event_stream_handler), carried
        # into deps so it reaches the orchestrator and every nested specialist.
        self._event_handler = event_handler

        # Wrap once so every agent and the CSV-parse call log their LLM requests
        # when FINKRIT_LOG_LLM is set (a no-op otherwise, and None stays None).
        model = wrap_model_for_logging(model)
        self._model = model
        # Every agent, not just the orchestrator: it combines specialist
        # replies as they came back, so one specialist answering in another
        # language is enough to produce a bilingual reply.
        self.risk = RiskAgent(model=model, language=language)
        self.performance = PerformanceAgent(model=model, language=language)
        self.optimization = OptimizationAgent(model=model, language=language)
        self.tax = TaxAgent(model=model, language=language)
        self._specialists = {
            "risk": self.risk,
            "performance": self.performance,
            "optimization": self.optimization,
            "tax": self.tax,
        }
        self.orchestrator = Orchestrator(
            model, self.risk, self.performance, self.optimization, self.tax,
            language=language,
        )

    @property
    def deps(self) -> AgentDeps:
        return AgentDeps(store=self._store, registry=self._registry, event_handler=self._event_handler)

    def register_portfolio(self, portfolio: Portfolio) -> None:
        self.desk.register_portfolio(portfolio)

    def list_portfolios(self) -> list[Portfolio]:
        return self.desk.list_portfolios()

    def register_asset(self, asset: Asset) -> None:
        self.desk.register_asset(asset)

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

    # The deterministic surface, delegated to finkritcore. Kept on Assistant
    # because it is what finkritserver and every notebook caller already reach
    # for, and because holding an Assistant should not mean losing access to the
    # half of the stack that needs no model.

    def report(
        self,
        portfolio_id: str,
        metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
    ) -> PortfolioRiskReport:
        return self.desk.report(portfolio_id, metrics)

    def tax_signals(self, portfolio_id: str, **kwargs) -> TaxSignalsReport:
        # The dashboard's actionable tax view (harvest candidates, wash sale
        # warnings, long term countdowns). kwargs pass through to
        # compose_tax_signals (rates, thresholds, as_of).
        return self.desk.tax_signals(portfolio_id, **kwargs)

    def prefetch_events(self, portfolio_id: str):
        # Warms the caches the dashboard endpoints read, yielding one event per
        # ticker as its download lands, so a consumer can draw a progress bar.
        return self.desk.prefetch_events(portfolio_id)

    def rebalance_compare(self, portfolio_id: str, **kwargs) -> dict:
        # The same fixed strategy menu the chat compare tool runs, through the
        # identical intel binding, so the two surfaces cannot disagree on a
        # number. kwargs pass through to the binding.
        return self.desk.rebalance_compare(portfolio_id, **kwargs)

    def _require_model(self) -> models.Model | models.KnownModelName | str:
        # Only reached once the deterministic mapper has declined, so the
        # message names the file rather than the feature: an upload as such
        # does not need a model, this particular one does.
        if self._model is None:
            raise RuntimeError(
                "This Assistant has no model configured, and this CSV could not "
                "be read without one. Its header needs to name the ticker, the "
                "quantity, the cost per share, and the acquired date, under any "
                "of the spellings finkritcore.ingest.CSV_ALIASES lists."
            )
        return self._model

    # Both paths try the deterministic mapper before the model. A file whose
    # header names ticker, quantity, cost per share, and acquired date is fully
    # readable in code, and handing it to a model instead costs a round trip
    # that returns what the header already said. On a local model that round
    # trip is minutes, long enough that the upload reads as broken.
    #
    # The model requirement is therefore checked only on the fallback: a clean
    # file uploads with no model configured and no key at all.

    def parse_portfolio_csv(
        self, csv_text: str, name: str = DEFAULT_PORTFOLIO_NAME
    ) -> ParsedPortfolio:
        # Sync convenience for scripts/notebooks. Does NOT register anything,
        # the caller reviews/corrects the result, then register_portfolio()s it.
        mapped = self.desk.parse_portfolio_csv(csv_text, name)
        if mapped is not None:
            return mapped
        return parse_portfolio_csv(csv_text, self._require_model())

    async def parse_portfolio_csv_async(
        self, csv_text: str, name: str = DEFAULT_PORTFOLIO_NAME
    ) -> ParsedPortfolio:
        # Async path for the web server's upload endpoint.
        mapped = self.desk.parse_portfolio_csv(csv_text, name)
        if mapped is not None:
            return mapped
        return await parse_portfolio_csv_async(csv_text, self._require_model())
