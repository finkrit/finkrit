# finagent/agent/base.py

from __future__ import annotations

from pydantic_ai import Agent, models
from pydantic_ai.usage import UsageLimits

from finkritintel.capability.base import Capability as FinkritCapability

from finagent.adapter.compiler import compile_capability
from finagent.deps import AgentDeps

# A spiraling tool loop (the model repeatedly re-calling tools without
# converging) burns tokens unbounded if nothing stops it. These are starting
# defaults, not tuned against real usage -- generous enough for a multi-metric
# risk question, bounded enough to fail fast on a runaway loop. Pass
# usage_limits=None to CapabilityAgent to opt out entirely.
DEFAULT_USAGE_LIMITS = UsageLimits(request_limit=15, tool_calls_limit=15)


class CapabilityAgent:
    """
    Wraps one finkritintel Capability into a conversational pydantic-ai
    Agent. The capability is the agent's toolset; the agent is defined by
    what it can do. One capability per agent, always-on (no defer_loading:
    a single-capability agent always needs its own tools).

    ``model`` is optional and the underlying pydantic-ai Agent is built lazily
    on first ``ask`` (F-1): a subclass's deterministic, no-LLM surface (e.g.
    ``RiskAgent.report``) must be usable with no model and no API key. Calling
    ``ask``/``ask_async`` without a model raises a clear error.

    ``usage_limits`` defaults to a bounded ``UsageLimits`` (F-5) so a
    spiraling tool loop can't burn tokens unbounded; pass ``None`` to disable.
    """

    def __init__(
        self,
        capability: FinkritCapability,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = "",
        usage_limits: UsageLimits | None = DEFAULT_USAGE_LIMITS,
    ) -> None:
        self._capability = capability
        self._model = model
        self._instructions = instructions
        self._usage_limits = usage_limits
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            if self._model is None:
                raise RuntimeError(
                    "This agent has no model configured; the conversational path "
                    "(ask/ask_async) requires one. The deterministic path does not."
                )
            self._agent = Agent(
                self._model,
                deps_type=AgentDeps,
                instructions=self._instructions,
                capabilities=[compile_capability(self._capability)],
            )
        return self._agent

    def ask(self, question: str, deps: AgentDeps) -> str:
        """
        Synchronous conversational turn -- for scripts, notebooks, the REPL.
        Spins up its own event loop under the hood (pydantic-ai run_sync).
        """
        return self.agent.run_sync(question, deps=deps, usage_limits=self._usage_limits).output

    async def ask_async(self, question: str, deps: AgentDeps) -> str:
        """
        Async conversational turn -- for servers (FastAPI) and concurrent
        callers already inside an event loop. Same result as ask(); this is
        the path the web layer uses. (Only the LLM loop is genuinely async
        here; the risk tools it calls remain sync and are threadpooled by
        pydantic-ai.)
        """
        result = await self.agent.run(question, deps=deps, usage_limits=self._usage_limits)
        return result.output
