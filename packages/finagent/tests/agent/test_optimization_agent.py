# finagent/tests/agent/test_optimization_agent.py
from __future__ import annotations

import warnings

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finkritintel.integration.finkritq import OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING

from finagent.agent.optimization import OPTIMIZATION_INSTRUCTIONS, OptimizationAgent
from finagent.deps import AgentDeps
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _deps() -> AgentDeps:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return AgentDeps(store=store, registry=make_registry())


class TestOptimizationBinding:
    """The live binding runs finkritq for real over the fake-data registry."""

    def test_min_variance_weights_are_long_only_and_sum_to_one(self):
        weights = OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING.execute(make_portfolio(), make_registry())
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        assert all(w >= -1e-9 for w in weights.values())


class TestOptimizationAgentAsk:
    """Conversational path, scripted FunctionModel, no network or model key."""

    def test_ask_answers_from_a_tool_call(self):
        def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            already = any(
                isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
            )
            if already:
                return ModelResponse(parts=[TextPart("Here is your minimum-variance allocation.")])
            return ModelResponse(
                parts=[ToolCallPart(tool_name="optimize_minimum_variance",
                                    args={"portfolio_id": "port-1"})]
            )

        agent = OptimizationAgent(model=FunctionModel(script))
        answer = agent.ask("What's the minimum-variance allocation?", _deps())
        assert isinstance(answer, str)
        assert "allocation" in answer.lower()


class TestOptimizationInstructions:

    def test_mentions_the_default_portfolio_id(self):
        assert DEFAULT_PORTFOLIO_ID in OPTIMIZATION_INSTRUCTIONS
