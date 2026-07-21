# finagent/tests/agent/test_performance_agent.py
from __future__ import annotations

import asyncio
import warnings
from datetime import date

import pytest

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.agent.performance import PERFORMANCE_INSTRUCTIONS, PerformanceAgent
from finagent.deps import AgentDeps
from finagent.report.performance import PerformanceMetric, PortfolioPerformanceReport
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore, PortfolioNotFoundError
from finagent.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _deps() -> AgentDeps:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return AgentDeps(store=store, registry=make_registry())


class TestPerformanceAgentReport:
    """Deterministic path -- no LLM. Uses a real (fake-data) registry."""

    def test_report_returns_portfolio_performance_report(self):
        agent = PerformanceAgent(model="test")
        report = agent.report("port-1", _deps())
        assert isinstance(report, PortfolioPerformanceReport)
        assert report.total_return is not None

    def test_report_respects_metric_selector(self):
        agent = PerformanceAgent(model="test")
        report = agent.report("port-1", _deps(), {PerformanceMetric.SHARPE_RATIO})
        assert report.sharpe_ratio is not None
        assert report.total_return is None

    def test_report_raises_for_unknown_portfolio(self):
        agent = PerformanceAgent(model="test")
        with pytest.raises(PortfolioNotFoundError):
            agent.report("does-not-exist", _deps())

    def test_report_threads_params_to_composer(self):
        # PerformanceAgent.report() is a thin pass-through to
        # compose_portfolio_performance_report; prove the extra params reach it.
        agent = PerformanceAgent(model="test")
        start, end = date(2023, 1, 1), date(2023, 6, 1)
        report = agent.report(
            "port-1", _deps(), {PerformanceMetric.SHARPE_RATIO},
            risk_free_rate=0.02, periods_per_year=52, start=start, end=end, interval="1wk",
        )
        assert report.params.risk_free_rate == 0.02
        assert report.params.periods_per_year == 52
        assert report.params.lookback_start == start
        assert report.params.lookback_end == end
        assert report.params.interval == "1wk"


class TestPerformanceAgentAsk:
    """Conversational path -- scripted FunctionModel, no network/model key."""

    def test_ask_answers_from_a_tool_call(self):
        def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            already = any(
                isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
            )
            if already:
                return ModelResponse(parts=[TextPart("Your Sharpe ratio is computed.")])
            return ModelResponse(
                parts=[ToolCallPart(tool_name="portfolio_sharpe_ratio", args={"portfolio_id": "port-1"})]
            )

        agent = PerformanceAgent(model=FunctionModel(script))
        answer = agent.ask("What's my Sharpe ratio?", _deps())
        assert isinstance(answer, str)
        assert "sharpe" in answer.lower()

    def test_ask_async_drives_the_same_tool_path(self):
        def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            already = any(
                isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
            )
            if already:
                return ModelResponse(parts=[TextPart("Your Sharpe ratio is computed.")])
            return ModelResponse(
                parts=[ToolCallPart(tool_name="portfolio_sharpe_ratio", args={"portfolio_id": "port-1"})]
            )

        agent = PerformanceAgent(model=FunctionModel(script))
        answer = asyncio.run(agent.ask_async("What's my Sharpe ratio?", _deps()))
        assert "sharpe" in answer.lower()


class TestPerformanceInstructions:

    def test_mentions_the_default_portfolio_id(self):
        assert DEFAULT_PORTFOLIO_ID in PERFORMANCE_INSTRUCTIONS
