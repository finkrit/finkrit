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
    """Calls portfolio_volatility on port-1, then answers in text."""
    answered = any(
        isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])
    )
    if answered:
        return ModelResponse(parts=[TextPart("Your portfolio's volatility has been computed.")])
    return ModelResponse(
        parts=[ToolCallPart(tool_name="portfolio_volatility", args={"portfolio_id": "port-1"})]
    )


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
