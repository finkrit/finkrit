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

import pytest

from finkritintel.capability.risk import RISK_CAPABILITY

from finagent.agent.base import DEFAULT_USAGE_LIMITS, CapabilityAgent
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
        # Substring rather than equality: the answer language is appended to
        # whatever instructions were given (see with_language).
        assert "Custom prompt text." in "".join(agent.agent._instructions)


    # --- F-1: model is optional; the pydantic-ai Agent builds lazily ---

    def test_constructs_without_a_model(self):
        # Must not raise -- a deterministic-only subclass never touches .agent.
        agent = CapabilityAgent(RISK_CAPABILITY, instructions="Be terse.")
        assert isinstance(agent, CapabilityAgent)

    def test_accessing_agent_without_a_model_raises_clearly(self):
        agent = CapabilityAgent(RISK_CAPABILITY, instructions="Be terse.")
        with pytest.raises(RuntimeError, match="no model configured"):
            _ = agent.agent

    # --- F-5: bounded UsageLimits by default, overridable ---

    def test_default_usage_limits_applied(self):
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Be terse.")
        assert agent._usage_limits is DEFAULT_USAGE_LIMITS

    def test_usage_limits_can_be_disabled(self):
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Be terse.", usage_limits=None)
        assert agent._usage_limits is None

    def test_custom_usage_limits_honored(self):
        from pydantic_ai.usage import UsageLimits

        custom = UsageLimits(request_limit=3)
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Be terse.", usage_limits=custom)
        assert agent._usage_limits is custom


class TestAnswerLanguage:
    """Nothing used to say what language to answer in, so a multilingual model
    picked, and picked differently from one question to the next."""

    def _instructions(self, **kwargs) -> str:
        agent = CapabilityAgent(RISK_CAPABILITY, model="test", instructions="Base.", **kwargs)
        return "".join(agent.agent._instructions)

    def test_english_is_the_default(self):
        assert "Answer in English." in self._instructions()

    def test_a_language_can_be_chosen(self):
        assert "Answer in Thai." in self._instructions(language="Thai")

    def test_stated_at_both_ends(self):
        # Observed on a local qwen2.5 14b: with the directive only at the end,
        # every specialist complied and the orchestrator answered in Thai. It
        # has to frame the instructions as well as close them.
        text = self._instructions()
        assert text.startswith("Answer in English.")
        assert text.rstrip().endswith("never translated or reformatted.")

    def test_the_question_language_does_not_decide(self):
        # The point of the setting: predictable output, not output that tracks
        # whatever language the user happened to type in.
        assert "whatever language the question was asked in" in self._instructions()

    def test_values_are_protected_from_translation(self):
        # A model translating its prose will localize a ticker or reformat a
        # percentage along with it, which breaks the one promise of the stack.
        text = self._instructions(language="Thai")
        assert "Tickers, numbers, dates, and metric names stay exactly as they are" in text

    def test_the_caller_instructions_survive(self):
        assert "Base." in self._instructions()
