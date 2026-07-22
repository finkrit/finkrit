# finagent/agent/orchestrator.py

from __future__ import annotations

from pydantic_ai import Agent, RunContext, models

from finagent.agent.base import DEFAULT_USAGE_LIMITS
from finagent.agent.optimization import OptimizationAgent
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.deps import AgentDeps
from finagent.store import DEFAULT_PORTFOLIO_ID

ORCHESTRATOR_INSTRUCTIONS = (
    "You are a portfolio assistant that delegates to specialist tools. Read the "
    "question, call the specialist(s) that can answer it, and combine their "
    "answers into one plain response. For a broad request (a review, or a "
    "question spanning risk, performance, and allocation) call several and "
    "synthesize. Pass each specialist a focused sub-question. Never invent or "
    "alter a number, report only what a specialist returned, and if a specialist "
    "cannot answer, say so. Allocations are proposals, not trades. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}', "
    "reference that id when a specialist asks about the portfolio."
)


class Orchestrator:
    """
    The all-encompassing router (Way C): a pydantic-ai agent whose tools each
    delegate to one specialist. The model picks one tool or several and
    synthesizes, so a multi-domain question is answered by fanning out. This
    costs an extra orchestration loop around every specialist it invokes, the
    direct single-specialist path (CapabilityAgent.ask) has no such overhead.

    Built lazily on first ask (like CapabilityAgent), so constructing an
    Assistant with no model stays cheap and keyless.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None,
        risk: RiskAgent,
        performance: PerformanceAgent,
        optimization: OptimizationAgent,
        instructions: str = ORCHESTRATOR_INSTRUCTIONS,
        usage_limits=DEFAULT_USAGE_LIMITS,
    ) -> None:
        self._model = model
        self._risk = risk
        self._performance = performance
        self._optimization = optimization
        self._instructions = instructions
        self._usage_limits = usage_limits
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            if self._model is None:
                raise RuntimeError(
                    "The orchestrator has no model configured, routing requires one."
                )
            agent = Agent(self._model, deps_type=AgentDeps, instructions=self._instructions)
            risk, performance, optimization = self._risk, self._performance, self._optimization

            @agent.tool
            async def ask_risk(ctx: RunContext[AgentDeps], question: str) -> str:
                """
                How risky the portfolio or a single asset is, and what could be lost.
                Covers volatility, variance, semivariance, downside deviation, drawdown
                and maximum drawdown, value at risk and conditional VaR, beta to a
                benchmark, and each holding's marginal and component contribution to
                risk. Pick this for questions about danger, downside, or spread. Not
                realized returns, which are performance.
                """
                return await risk.ask_async(question, ctx.deps)

            @agent.tool
            async def ask_performance(ctx: RunContext[AgentDeps], question: str) -> str:
                """
                How the portfolio has performed over the window. Covers total return
                (cumulative), annualized return (per year), and the risk-adjusted ratios
                Sharpe, Sortino, and Calmar. Pick this for how did I do and
                risk-adjusted return questions. Not forward-looking risk (that is risk),
                and it does not do attribution yet.
                """
                return await performance.ask_async(question, ctx.deps)

            @agent.tool
            async def ask_optimization(ctx: RunContext[AgentDeps], question: str) -> str:
                """
                What the target allocation should be. Covers the minimum-variance
                (lowest-risk) and maximum-Sharpe (best risk-adjusted) optimal weights,
                long-only. Pick this for what should I hold, optimize, or rebalance
                questions. Not for measuring the current portfolio, which is risk or
                performance. The weights are proposed allocations, not trades.
                """
                return await optimization.ask_async(question, ctx.deps)

            self._agent = agent
        return self._agent

    def ask(self, question: str, deps: AgentDeps) -> str:
        return self.agent.run_sync(
            question, deps=deps, usage_limits=self._usage_limits,
            event_stream_handler=deps.event_handler,
        ).output

    async def ask_async(self, question: str, deps: AgentDeps) -> str:
        result = await self.agent.run(
            question, deps=deps, usage_limits=self._usage_limits,
            event_stream_handler=deps.event_handler,
        )
        return result.output
