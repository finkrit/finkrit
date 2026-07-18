# finagent/tests/agent/test_risk_agent.py
from __future__ import annotations

import asyncio
import warnings
from datetime import date

import pytest

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.agent.risk import RISK_INSTRUCTIONS, RiskAgent
from finagent.deps import AgentDeps
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore, PortfolioNotFoundError
from finagent.tests.fixtures import make_portfolio, make_registry, make_stock

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

    def test_report_raises_for_unknown_portfolio(self):
        agent = RiskAgent(model="test")
        with pytest.raises(PortfolioNotFoundError):
            agent.report("does-not-exist", _deps())

    def test_report_threads_benchmark_start_end_interval_to_composer(self):
        # RiskAgent.report() is a thin pass-through to compose_portfolio_risk_report;
        # prove the four extra params actually reach it rather than being dropped.
        agent = RiskAgent(model="test")
        start, end = date(2023, 1, 1), date(2023, 6, 1)
        report = agent.report(
            "port-1", _deps(), {RiskMetric.BETA},
            benchmark=make_stock("QQQ"), start=start, end=end, interval="1wk",
        )
        assert report.params.benchmark_ticker == "QQQ"
        assert report.params.lookback_start == start
        assert report.params.lookback_end == end
        assert report.params.interval == "1wk"


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

    def test_ask_async_drives_the_same_tool_path(self):
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
        answer = asyncio.run(agent.ask_async("What's my portfolio volatility?", _deps()))
        assert "volatility" in answer.lower()

    def test_ask_resolves_without_the_user_naming_a_portfolio(self):
        # Single-portfolio product: the user never says an id ("what's my
        # volatility?"), so the model must fall back to DEFAULT_PORTFOLIO_ID --
        # which is only possible because RISK_INSTRUCTIONS tells it that id.
        # The portfolio here is registered under that same default id, proving
        # the whole chain (instructions -> model's tool call -> store lookup)
        # is consistent, not just that the constant exists somewhere.
        store = InMemoryStore()
        store.register_portfolio(make_portfolio(DEFAULT_PORTFOLIO_ID))
        deps = AgentDeps(store=store, registry=make_registry())

        def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            already = any(
                isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
            )
            if already:
                return ModelResponse(parts=[TextPart("Your annualized volatility is computed.")])
            return ModelResponse(
                parts=[ToolCallPart(
                    tool_name="portfolio_volatility",
                    args={"portfolio_id": DEFAULT_PORTFOLIO_ID},
                )]
            )

        agent = RiskAgent(model=FunctionModel(script))
        answer = agent.ask("What's my portfolio's volatility?", deps)  # no id mentioned
        assert "volatility" in answer.lower()


class TestRiskInstructions:

    def test_mentions_the_default_portfolio_id(self):
        assert DEFAULT_PORTFOLIO_ID in RISK_INSTRUCTIONS
