# finkritserver/tests/conftest.py
"""
Shared fixtures: an Assistant wired to a fake registry (no network) and a
scripted FunctionModel (no API key), plus a TestClient over the app.
Reuses finagent's fake HistoryProvider so data behavior matches finagent tests.
"""
from __future__ import annotations

import warnings

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.assistant import Assistant
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_registry

from finkritserver.app import create_app

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _script_volatility(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Scripted model that drives the whole /ask path.

    The dashboard routes through the orchestrator, so this one function is
    invoked for two kinds of agent, each with its own tools and its own message
    history, and branches on which tools it was handed. On the orchestrator it
    delegates to the risk specialist via ask_risk. On that specialist it calls
    portfolio_volatility. Each answers in text once its call has returned.
    """
    tool_names = {t.name for t in info.function_tools}
    answered = any(
        isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
    )
    if answered:
        return ModelResponse(parts=[TextPart("Your portfolio's volatility has been computed.")])
    if "ask_risk" in tool_names:
        return ModelResponse(
            parts=[ToolCallPart(tool_name="ask_risk", args={"question": "What is the volatility?"})]
        )
    if "portfolio_volatility" in tool_names:
        return ModelResponse(
            parts=[ToolCallPart(tool_name="portfolio_volatility", args={"portfolio_id": "port-1"})]
        )
    return ModelResponse(parts=[TextPart("Your portfolio's volatility has been computed.")])


@pytest.fixture
def assistant() -> Assistant:
    return Assistant(
        model=FunctionModel(_script_volatility),
        store=InMemoryStore(),
        registry=make_registry(),
    )


@pytest.fixture
def client(assistant: Assistant) -> TestClient:
    return TestClient(create_app(assistant))


@pytest.fixture
def portfolio_payload() -> dict:
    """A minimal two-holding portfolio (single-asset portfolios degenerate in
    finkritq's covariance math)."""
    return {
        "id": "port-1",
        "name": "Test Portfolio",
        "holdings": [
            {"ticker": "AAA", "quantity": 10, "cost_per_share": 100, "acquired": "2024-01-02"},
            {"ticker": "BBB", "quantity": 5, "cost_per_share": 120, "acquired": "2024-01-02"},
        ],
    }
