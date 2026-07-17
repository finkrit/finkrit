# finagent/tests/agent/test_risk_agent.py
from __future__ import annotations

import warnings

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.agent.risk import RiskAgent
from finagent.deps import AgentDeps
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _deps() -> AgentDeps:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return AgentDeps(store=store, registry=make_registry())


class TestRiskAgentReport:
    """Deterministic path -- no LLM. Uses a real (fake-data) registry."""

    def test_report_returns_portfolio_risk_report(self):
        agent = RiskAgent(model="test")
        report = agent.report("port-1", _deps())
        assert isinstance(report, PortfolioRiskReport)
        assert report.volatility is not None

    def test_report_respects_metric_selector(self):
        agent = RiskAgent(model="test")
        report = agent.report("port-1", _deps(), {RiskMetric.MAX_DRAWDOWN})
        assert report.max_drawdown is not None
        assert report.volatility is None


class TestRiskAgentAsk:
    """Conversational path -- scripted FunctionModel, no network/model key."""

    def test_ask_answers_from_a_tool_call(self):
        def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            already = any(
                isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
            )
            if already:
                return ModelResponse(parts=[TextPart("Your annualized volatility is computed.")])
            return ModelResponse(
                parts=[ToolCallPart(tool_name="portfolio_volatility", args={"portfolio_id": "port-1"})]
            )

        agent = RiskAgent(model=FunctionModel(script))
        answer = agent.ask("What's my portfolio volatility?", _deps())
        assert isinstance(answer, str)
        assert "volatility" in answer.lower()
