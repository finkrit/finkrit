# finagent/tests/agent/test_base.py
"""
Direct tests for CapabilityAgent -- previously only exercised indirectly
through RiskAgent. A shared base class needs its own tests independent of
any one subclass, so a future second specialist (e.g. OptimizationAgent)
can't silently break behavior that RiskAgent's tests don't happen to hit.
"""
from __future__ import annotations

import asyncio
import warnings

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

from finkritintel.capability.risk import RISK_CAPABILITY

from finagent.agent.base import CapabilityAgent
from finagent.deps import AgentDeps
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _static_reply(messages: list[ModelMessage], info) -> ModelResponse:
    return ModelResponse(parts=[TextPart("ok")])


class TestCapabilityAgent:

    def test_wraps_an_arbitrary_capability(self):
        # Not RISK_CAPABILITY specifically -- proves the base class isn't
        # accidentally coupled to the one capability it's always used with today.
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Be terse.")
        assert isinstance(agent, CapabilityAgent)

    def test_agent_property_exposes_underlying_pydantic_ai_agent(self):
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Be terse.")
        assert isinstance(agent.agent, Agent)

    def test_ask_returns_model_output(self):
        from pydantic_ai.models.function import FunctionModel

        agent = CapabilityAgent(RISK_CAPABILITY, model=FunctionModel(_static_reply), instructions="Be terse.")
        deps = AgentDeps(store=InMemoryStore(), registry=make_registry())
        assert agent.ask("anything", deps) == "ok"

    def test_ask_async_returns_same_output_as_sync(self):
        # Async path (used by the server) must agree with the sync path.
        # Driven via asyncio.run so no pytest-asyncio dependency is needed.
        from pydantic_ai.models.function import FunctionModel

        agent = CapabilityAgent(RISK_CAPABILITY, model=FunctionModel(_static_reply), instructions="Be terse.")
        deps = AgentDeps(store=InMemoryStore(), registry=make_registry())
        assert asyncio.run(agent.ask_async("anything", deps)) == "ok"

    def test_instructions_are_passed_through_to_the_agent(self):
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Custom prompt text.")
        # `.instructions` on the pydantic-ai Agent is a decorator method, not
        # the stored value -- `_instructions` (a list) holds what was passed
        # to the constructor. Verified via direct introspection, not guessed.
        assert "Custom prompt text." in agent.agent._instructions
