# finagent/tests/test_assistant.py
from __future__ import annotations

import warnings

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.agent.risk import RiskAgent
from finagent.assistant import Assistant
from finagent.deps import AgentDeps
from finagent.report.report import PortfolioRiskReport
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _script_portfolio_volatility_call(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    already_called = any(
        isinstance(part, ToolReturnPart) for msg in messages for part in getattr(msg, "parts", [])
    )
    if already_called:
        return ModelResponse(parts=[TextPart("Your portfolio's volatility has been computed.")])
    return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_volatility", args={"portfolio_id": "port-1"})])


@pytest.fixture
def assistant() -> Assistant:
    return Assistant(model="test", store=InMemoryStore(), registry=make_registry())


class TestAssistant:

    def test_requires_explicit_model(self):
        with pytest.raises(TypeError):
            Assistant()  # type: ignore[call-arg]

    def test_auto_registers_sp500_benchmark(self, assistant: Assistant):
        assert assistant._store.get_asset("^GSPC").ticker == "^GSPC"

    def test_exposes_risk_specialist(self, assistant: Assistant):
        assert isinstance(assistant.risk, RiskAgent)

    def test_deps_carry_store_and_registry(self, assistant: Assistant):
        deps = assistant.deps
        assert isinstance(deps, AgentDeps)
        assert deps.store is assistant._store

    def test_register_portfolio_makes_it_resolvable(self, assistant: Assistant):
        portfolio = make_portfolio()
        assistant.register_portfolio(portfolio)
        assert assistant._store.get_portfolio("port-1") is portfolio

    def test_report_delegates_to_risk_agent(self, assistant: Assistant):
        assistant.register_portfolio(make_portfolio())
        report = assistant.report("port-1")
        assert isinstance(report, PortfolioRiskReport)
        assert report.volatility is not None

    def test_ask_answers_a_real_risk_question(self):
        model = FunctionModel(_script_portfolio_volatility_call)
        assistant = Assistant(model=model, store=InMemoryStore(), registry=make_registry())
        assistant.register_portfolio(make_portfolio())

        result = assistant.ask("What's my portfolio's volatility?")

        assert isinstance(result, str)
        assert "volatility" in result.lower()
