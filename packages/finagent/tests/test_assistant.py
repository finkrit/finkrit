# finagent/tests/test_assistant.py
from __future__ import annotations

import asyncio
import warnings

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finkritq.data import DataRegistry
from finkritq.data.providers import MemoizingHistoryProvider, YFinanceProvider

from finagent.agent.risk import RiskAgent
from finagent.assistant import Assistant, _default_registry
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

    def test_report_works_without_a_model(self):
        # F-1: the deterministic dashboard path needs no LLM and no API key.
        assistant = Assistant(store=InMemoryStore(), registry=make_registry())
        assistant.register_portfolio(make_portfolio())
        report = assistant.report("port-1")
        assert isinstance(report, PortfolioRiskReport)
        assert report.volatility is not None

    def test_ask_without_a_model_raises_clearly(self):
        assistant = Assistant(store=InMemoryStore(), registry=make_registry())
        assistant.register_portfolio(make_portfolio())
        with pytest.raises(RuntimeError, match="no model configured"):
            assistant.ask("what's my volatility?")

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

    def test_ask_async_answers_the_same_question(self):
        # The path the FastAPI server will call. asyncio.run avoids needing
        # a pytest-asyncio plugin.
        model = FunctionModel(_script_portfolio_volatility_call)
        assistant = Assistant(model=model, store=InMemoryStore(), registry=make_registry())
        assistant.register_portfolio(make_portfolio())

        result = asyncio.run(assistant.ask_async("What's my portfolio's volatility?"))

        assert isinstance(result, str)
        assert "volatility" in result.lower()

    def test_defaults_to_in_memory_store_when_none_given(self):
        # No `store=` passed -- the actual "just pip install and go" path.
        assistant = Assistant(model="test", registry=make_registry())
        assert isinstance(assistant._store, InMemoryStore)

    def test_defaults_to_default_registry_when_none_given(self):
        # No `registry=` passed either -- exercises _default_registry() for
        # real, not the fake registry every other test substitutes in.
        assistant = Assistant(model="test", store=InMemoryStore())
        assert isinstance(assistant._registry, DataRegistry)


class TestDefaultRegistry:
    """
    _default_registry() wires YFinanceProvider + MemoizingHistoryProvider.
    Construction never hits the network (only .history()/.snapshot() calls
    would), so this is safe to test directly without a live fetch.
    """

    def test_returns_a_data_registry(self):
        assert isinstance(_default_registry(), DataRegistry)

    def test_history_provider_is_memoized(self):
        registry = _default_registry()
        assert isinstance(registry._history_provider, MemoizingHistoryProvider)

    def test_memoized_provider_wraps_yfinance(self):
        registry = _default_registry()
        assert isinstance(registry._history_provider._wrapped, YFinanceProvider)

    def test_snapshot_provider_is_registered_and_unwrapped(self):
        # Snapshots aren't memoized (a snapshot is a live quote, not history) --
        # confirm it's wired to a real provider and NOT accidentally left unset.
        registry = _default_registry()
        assert isinstance(registry._snapshot_provider, YFinanceProvider)
