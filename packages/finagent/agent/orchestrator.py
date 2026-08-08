# finagent/agent/orchestrator.py

from __future__ import annotations

from pydantic_ai import Agent, RunContext, models
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage

from finkritcore.store import DEFAULT_PORTFOLIO_ID

from finagent.agent.base import (
    DEFAULT_LANGUAGE,
    DEFAULT_TOOL_RETRIES,
    ORCHESTRATOR_USAGE_LIMITS,
    with_language,
)
from finagent.agent.optimization import OptimizationAgent
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.agent.tax import TaxAgent
from finagent.deps import AgentDeps


ORCHESTRATOR_INSTRUCTIONS = (
    "You are a portfolio assistant that delegates to specialist tools. Read the "
    "question, call the specialist(s) that can answer it, and combine their "
    "answers into one plain response. For a broad request (a review, or a "
    "question spanning risk, performance, and allocation) call several and "
    "synthesize. Pass each specialist a focused sub-question. Never invent or "
    "alter a number, report only what a specialist returned, and if a specialist "
    "cannot answer, say so. Allocations are proposals, not trades. "
    # Two rewrites, two different failures, so this one leads with an example
    # rather than a rule. "Reference that id" was read as "pass portfolio_id",
    # which these tools do not accept. Replacing it with "write the id inside
    # the question text" was then taken literally: the model sent the single
    # word "primary" as the whole question, and the specialist, given nothing
    # to answer, asked the user for clarification. Talking about arguments and
    # parameters at all also seems to invite schema shaped output, one run
    # sending {"type": "string", "value": "..."} in place of the string.
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}'. "
    "Hand each specialist a complete question in plain words, with the portfolio "
    f'id inside it. For example: "what is the volatility of portfolio '
    f'{DEFAULT_PORTFOLIO_ID}?". Never send the id on its own and never send an '
    "object or a schema. "
    # The third failure, and the first that only shows in a threaded
    # conversation. "Never repeat the same question twice" was written when
    # every run was fresh, so it could only ever have meant "within this run".
    # Once history was threaded, the model could see a question it had already
    # asked on an earlier turn, read the ban as covering that one too, and
    # resolve the conflict by printing the tool call as a markdown JSON block
    # and saying "I will proceed by calling these tools now". It never called
    # anything. Observed on the first turn that needed a call already present
    # in history, and on every turn after it.
    "When you need a specialist, call it. Never write a tool call out as text, "
    "never describe a call you are about to make, and never say you will "
    "proceed: calling the tool is the only way to reach a specialist. Earlier "
    "turns are context, not a record of what you are allowed to ask again. "
    "Asking a specialist the same thing on a later turn is fine when the user "
    "asks again. What is not fine is asking it the same thing twice while "
    "answering one question."
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
        tax: TaxAgent,
        instructions: str = ORCHESTRATOR_INSTRUCTIONS,
        usage_limits=ORCHESTRATOR_USAGE_LIMITS,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._model = model
        self._risk = risk
        self._performance = performance
        self._optimization = optimization
        self._tax = tax
        # Pinned here as well as on each specialist. This one governs the
        # combined reply, the specialists govern the parts it is combining, and
        # a mismatch between the two reads as a bilingual answer.
        self._instructions = with_language(instructions, language)
        self._usage_limits = usage_limits
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            if self._model is None:
                raise RuntimeError(
                    "The orchestrator has no model configured, routing requires one."
                )
            agent = Agent(
                self._model,
                deps_type=AgentDeps,
                instructions=self._instructions,
                retries=DEFAULT_TOOL_RETRIES,
            )
            risk, performance, optimization, tax = (
                self._risk, self._performance, self._optimization, self._tax,
            )

            @agent.tool
            async def ask_risk(ctx: RunContext[AgentDeps], question: str) -> str:
                """
                How risky the portfolio is, how risky each holding in it is, and
                what could be lost. Covers volatility, variance, semivariance,
                downside deviation, drawdown and maximum drawdown, value at risk
                and conditional VaR, beta to a benchmark, and each holding's
                marginal and component contribution to risk. Answers questions
                about every holding at once, so pass those through whole rather
                than splitting them per ticker. Pick this for danger, downside,
                or spread. Not realized returns, which are performance.
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

            @agent.tool
            async def ask_tax(ctx: RunContext[AgentDeps], question: str) -> str:
                """
                The portfolio's current tax position at today's prices. Covers
                unrealized capital gains and losses, tax-loss harvesting candidates
                (lots trading below cost, net of the wash sale window), and the split
                of value between long term and short term holdings. Pick this for
                gains, losses, harvesting, and long-versus-short-term tax questions.
                Read-only, it describes the tax position and does not trade or
                rebalance.
                """
                return await tax.ask_async(question, ctx.deps)

            self._agent = agent
        return self._agent

    # run/run_async return the full result, which carries the updated message
    # history. Only the orchestrator's own messages are threaded, a specialist's
    # internal loop happens inside a tool call and stays ephemeral, so history
    # tracks the conversation the user actually had.

    def run(
        self,
        question: str,
        deps: AgentDeps,
        message_history: list[ModelMessage] | None = None,
    ) -> AgentRunResult:
        return self.agent.run_sync(
            question, deps=deps, usage_limits=self._usage_limits,
            event_stream_handler=deps.event_handler,
            message_history=message_history,
        )

    async def run_async(
        self,
        question: str,
        deps: AgentDeps,
        message_history: list[ModelMessage] | None = None,
    ) -> AgentRunResult:
        return await self.agent.run(
            question, deps=deps, usage_limits=self._usage_limits,
            event_stream_handler=deps.event_handler,
            message_history=message_history,
        )

    # answer_of, not result.output: when only one specialist answered there is
    # nothing to combine, and the orchestrator's closing text is a second
    # generation over numbers it must not alter. See conversation.answer_of.
    # Imported inside the methods because conversation imports the specialist
    # tool names this module defines, and a module level import would close
    # that loop.

    def ask(self, question: str, deps: AgentDeps) -> str:
        from finagent.conversation import answer_of

        return answer_of(self.run(question, deps))

    async def ask_async(self, question: str, deps: AgentDeps) -> str:
        from finagent.conversation import answer_of

        result = await self.run_async(question, deps)
        return answer_of(result)
