# finagent/agent/base.py

from __future__ import annotations

from pydantic_ai import Agent, models

from finkritintel.capability.base import Capability as FinkritCapability

from finagent.adapter.compiler import compile_capability
from finagent.deps import AgentDeps


class CapabilityAgent:
    """
    Wraps one finkritintel Capability into a conversational pydantic-ai
    Agent. The capability is the agent's toolset; the agent is defined by
    what it can do. One capability per agent, always-on (no defer_loading:
    a single-capability agent always needs its own tools).
    """

    def __init__(
        self,
        capability: FinkritCapability,
        model: models.Model | models.KnownModelName | str,
        instructions: str,
    ) -> None:
        self._capability = capability
        self._agent = Agent(
            model,
            deps_type=AgentDeps,
            instructions=instructions,
            capabilities=[compile_capability(capability)],
        )

    @property
    def agent(self) -> Agent:
        return self._agent

    def ask(self, question: str, deps: AgentDeps) -> str:
        return self._agent.run_sync(question, deps=deps).output
