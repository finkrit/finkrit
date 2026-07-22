# finagent/tests/agent/test_orchestrator.py
from __future__ import annotations

import warnings

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from finagent.agent.optimization import OptimizationAgent
from finagent.agent.orchestrator import ORCHESTRATOR_INSTRUCTIONS, Orchestrator
from finagent.agent.performance import PerformanceAgent
from finagent.agent.risk import RiskAgent
from finagent.deps import AgentDeps
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _deps() -> AgentDeps:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return AgentDeps(store=store, registry=make_registry())


def _has_tool_return(messages) -> bool:
    return any(isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", []))


# Specialist-level scripts: call the finq tool once (real computation on fake
# data), then answer in text.
def _risk_script(messages, info) -> ModelResponse:
    if _has_tool_return(messages):
        return ModelResponse(parts=[TextPart("Your annualized volatility is 12%.")])
    return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_volatility",
                                             args={"portfolio_id": "port-1"})])


def _opt_script(messages, info) -> ModelResponse:
    if _has_tool_return(messages):
        return ModelResponse(parts=[TextPart("Minimum-variance allocation computed.")])
    return ModelResponse(parts=[ToolCallPart(tool_name="optimize_minimum_variance",
                                             args={"portfolio_id": "port-1"})])


def _specialists():
    return (
        RiskAgent(model=FunctionModel(_risk_script)),
        PerformanceAgent(model=FunctionModel(_risk_script)),
        OptimizationAgent(model=FunctionModel(_opt_script)),
    )


class TestOrchestratorDelegation:

    def test_routes_a_single_question_to_one_specialist(self):
        def orch_script(messages, info) -> ModelResponse:
            if _has_tool_return(messages):
                return ModelResponse(parts=[TextPart("Risk summary: volatility is 12%.")])
            return ModelResponse(parts=[ToolCallPart(tool_name="ask_risk",
                                                     args={"question": "volatility"})])

        risk, performance, optimization = _specialists()
        orchestrator = Orchestrator(FunctionModel(orch_script), risk, performance, optimization)
        answer = orchestrator.ask("how risky am I?", _deps())
        assert "volatility" in answer.lower()

    def test_fans_out_to_two_specialists(self):
        # The orchestrator calls ask_risk AND ask_optimization in one turn, each
        # runs its own sub-agent loop over finq, then it combines them.
        def orch_script(messages, info) -> ModelResponse:
            if _has_tool_return(messages):
                return ModelResponse(parts=[TextPart("Combined risk and allocation view.")])
            return ModelResponse(parts=[
                ToolCallPart(tool_name="ask_risk", args={"question": "volatility"}),
                ToolCallPart(tool_name="ask_optimization", args={"question": "min variance"}),
            ])

        risk, performance, optimization = _specialists()
        orchestrator = Orchestrator(FunctionModel(orch_script), risk, performance, optimization)
        answer = orchestrator.ask("give me a review", _deps())
        assert isinstance(answer, str) and answer


class TestOrchestratorInstructions:

    def test_mentions_the_default_portfolio_id(self):
        assert DEFAULT_PORTFOLIO_ID in ORCHESTRATOR_INSTRUCTIONS
