# finagent/agent/base.py

from __future__ import annotations

from pydantic_ai import Agent, models
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import UsageLimits

from finkritintel.capability.base import Capability as FinkritCapability

from finagent.adapter.compiler import compile_capability
from finagent.deps import AgentDeps

# A spiraling tool loop (the model repeatedly re-calling tools without
# converging) burns tokens unbounded if nothing stops it. Pass
# usage_limits=None to CapabilityAgent to opt out entirely.
#
# Both budgets below are per run, and a specialist invoked by the orchestrator
# is its own run with its own fresh allowance (usage is not threaded through
# the delegation). So a four way fan out can spend the orchestrator's budget
# plus four specialist budgets. That is deliberate: one ceiling covering the
# whole tree would make a broad review compete against itself, where the last
# specialist asked fails for no reason but running last.


def _limits(tool_calls: int) -> UsageLimits:
    """A budget of ``tool_calls``, with the request ceiling derived from it.

    A model that batches its calls spends far fewer requests than tool calls.
    One that issues them singly, which is what a local model does, spends
    exactly one request per call plus one more to write the answer. Sizing for
    the serial case leaves the tool count as the only ceiling that ever bites,
    so a run that dies says how much work it tried to do rather than how many
    times it happened to speak to the model.
    """
    return UsageLimits(request_limit=tool_calls + 1, tool_calls_limit=tool_calls)


# The orchestrator's tools are the four specialists, so its budget counts
# delegations, not metrics. Four covers asking every one of them, the remaining
# four are room to go back to one after reading another's answer. An
# orchestrator reaching for a ninth delegation has asked someone three times
# and is looping rather than working.
ORCHESTRATOR_USAGE_LIMITS = _limits(8)

# A specialist's budget counts metrics. The widest honest question is a full
# risk review (volatility, VaR, conditional VaR, maximum drawdown, beta, and
# the marginal and component contribution breakdowns), which is seven or eight
# distinct tools out of the twenty risk exposes. Each rejected call spends one
# more, up to DEFAULT_TOOL_RETRIES below. Twelve is the widest real question
# plus a correction on roughly half of it.
#
# Not sized for "that metric for every holding", which is one call per holding
# and grows with the portfolio. Twelve holdings already overflow this and two
# hundred would overflow any number worth setting. That shape needs the
# question decomposed, not the ceiling raised.
SPECIALIST_USAGE_LIMITS = _limits(12)

# The name CapabilityAgent has always defaulted to. A CapabilityAgent is a
# specialist, the orchestrator is the one exception and asks for its own.
DEFAULT_USAGE_LIMITS = SPECIALIST_USAGE_LIMITS

# How many times a tool may hand the model an error and ask it to try again.
# pydantic-ai defaults to 1, which is one chance to read a message like
# "unknown ticker ZZZZ" and correct the call. A strong model rarely needs even
# that. A local one often gets an enum or a ticker wrong twice before it
# reads the error properly, and the run dies with "exceeded max retries"
# rather than answering. Two chances, still bounded, and the tool call limit
# above remains the real backstop against a loop.
DEFAULT_TOOL_RETRIES = 2

# The language every agent answers in. Nothing used to say, so a multilingual
# model was free to pick, and one that leans non English will answer in its own
# language intermittently, which is worse than doing it consistently.
DEFAULT_LANGUAGE = "English"


def with_language(instructions: str, language: str = DEFAULT_LANGUAGE) -> str:
    """``instructions`` with the answer language pinned.

    Applied to every agent, not only the orchestrator: the orchestrator
    combines specialist replies as they came back, so a specialist answering in
    another language produces a bilingual reply no matter what the orchestrator
    was told.

    The second sentence is the load bearing one. A model translating its prose
    will cheerfully localize a ticker or reformat a percentage along with it,
    and the whole premise of this stack is that computed values reach the
    reader exactly as the engine produced them.

    Stated twice, opening and closing, rather than appended once. Observed on
    a local qwen2.5 14b: with the directive only at the end, every specialist
    complied and the orchestrator answered in Thai. The orchestrator writes the
    longest reply and writes it last, which is where drift shows, so the
    directive needs to frame the instructions as well as close them.

    An instruction, not a guarantee. A small model will comply most of the time
    and drift occasionally, usually on the longest answer in the run.
    """
    return (
        f"Answer in {language}. "
        f"{instructions} "
        f"Your entire reply must be written in {language}, whatever language "
        f"the question was asked in. Tickers, numbers, dates, and metric names "
        f"stay exactly as they are, never translated or reformatted."
    )


class CapabilityAgent:
    """
    Wraps one finkritintel Capability into a conversational pydantic-ai
    Agent. The capability is the agent's toolset, the agent is defined by
    what it can do. One capability per agent, always-on (no defer_loading:
    a single-capability agent always needs its own tools).

    ``model`` is optional and the underlying pydantic-ai Agent is built lazily
    on first ``ask`` (F-1): a subclass's deterministic, no-LLM surface (e.g.
    ``RiskAgent.report``) must be usable with no model and no API key. Calling
    ``ask``/``ask_async`` without a model raises a clear error.

    ``usage_limits`` defaults to a bounded ``UsageLimits`` (F-5) so a
    spiraling tool loop can't burn tokens unbounded, pass ``None`` to disable.

    ``language`` pins the answer language onto whatever instructions are given
    (see ``with_language``). It is applied here rather than baked into each
    agent's instruction constant, so a caller supplying its own instructions
    still gets the language it asked for.
    """

    def __init__(
        self,
        capability: FinkritCapability,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = "",
        usage_limits: UsageLimits | None = DEFAULT_USAGE_LIMITS,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._capability = capability
        self._model = model
        self._instructions = with_language(instructions, language)
        self._usage_limits = usage_limits
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            if self._model is None:
                raise RuntimeError(
                    "This agent has no model configured, the conversational path "
                    "(ask/ask_async) requires one. The deterministic path does not."
                )
            self._agent = Agent(
                self._model,
                deps_type=AgentDeps,
                instructions=self._instructions,
                retries=DEFAULT_TOOL_RETRIES,
                capabilities=[compile_capability(self._capability)],
            )
        return self._agent

    # run/run_async return the full pydantic-ai result, which carries the
    # updated message history. Conversation uses these to thread a multi-turn
    # exchange. ask/ask_async stay the simple surface and return just the answer.

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

    def ask(self, question: str, deps: AgentDeps) -> str:
        """
        Synchronous conversational turn for usage in scripts, notebooks, the REPL.
        Spins up its own event loop under the hood (pydantic-ai run_sync).
        ``deps.event_handler``, if set, streams tool-call events live.

        Single turn with no memory of previous ones. For a threaded exchange use
        Conversation, which carries the message history across turns.
        """
        return self.run(question, deps).output

    async def ask_async(self, question: str, deps: AgentDeps) -> str:
        """
        Async conversational turn for servers (FastAPI etc.) and concurrent
        callers already inside an event loop. Same result as ask(), this is
        the path the web layer uses. (Only the LLM loop is genuinely async
        here, the risk tools it calls remain sync and are threadpooled by
        pydantic-ai.)
        """
        result = await self.run_async(question, deps)
        return result.output
