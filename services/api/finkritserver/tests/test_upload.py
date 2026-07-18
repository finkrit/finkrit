# finkritserver/tests/test_upload.py
"""
Tests for POST /api/portfolio/upload. Uses its own Assistant/model fixture
(not the shared `assistant` fixture in conftest.py, which scripts
portfolio_volatility tool calls for the /api/ask tests) -- the ingest agent
has no tools, only the hidden `final_result` structured-output tool.
"""
from __future__ import annotations

import io
import warnings

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.assistant import Assistant
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_registry

from finkritserver.app import create_app

warnings.filterwarnings("ignore", message="Could not generate return schema")

_PARSED_ARGS = {
    "name": "Uploaded Portfolio",
    "holdings": [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "cost_per_share": 150.0,
            "acquired": "2023-01-15",
        }
    ],
    "warnings": ["Assumed 'Cost' column was per-share."],
}


def _script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(tool_name="final_result", args=_PARSED_ARGS)])


@pytest.fixture
def upload_assistant() -> Assistant:
    return Assistant(model=FunctionModel(_script), store=InMemoryStore(), registry=make_registry())


@pytest.fixture
def upload_client(upload_assistant: Assistant) -> TestClient:
    return TestClient(create_app(upload_assistant, static_dir=None))


class TestUploadPortfolio:

    def test_parses_csv_and_returns_parsed_portfolio(self, upload_client: TestClient):
        csv_bytes = b"Symbol,Shares,Cost,Date\nAAPL,10,150.0,2023-01-15"
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Uploaded Portfolio"
        assert body["holdings"][0]["ticker"] == "AAPL"

    def test_surfaces_warnings_for_user_review(self, upload_client: TestClient):
        csv_bytes = b"Symbol,Shares,Cost,Date\nAAPL,10,150.0,2023-01-15"
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert "Assumed 'Cost' column was per-share." in r.json()["warnings"]

    def test_does_not_register_anything(self, upload_client: TestClient, upload_assistant: Assistant):
        csv_bytes = b"Symbol,Shares\nAAPL,10"
        upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert upload_assistant.list_portfolios() == []

    def test_rejects_non_csv_extension(self, upload_client: TestClient):
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.xlsx", io.BytesIO(b"whatever"), "application/octet-stream")},
        )
        assert r.status_code == 400
        assert "csv" in r.json()["detail"].lower()

    def test_rejects_oversized_file(self, upload_client: TestClient):
        huge = b"a" * (512_000 + 1)
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(huge), "text/csv")},
        )
        assert r.status_code == 400
        assert "too large" in r.json()["detail"].lower()

    def test_rejects_non_utf8_content(self, upload_client: TestClient):
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(b"\xff\xfe\x00bad"), "text/csv")},
        )
        assert r.status_code == 400
        assert "utf-8" in r.json()["detail"].lower()

    def test_upload_then_confirm_via_existing_register_endpoint(self, upload_client: TestClient):
        # The full flow: parse (no side effect) -> frontend review/correction
        # -> commit via the existing POST /api/portfolio.
        csv_bytes = b"Symbol,Shares,Cost,Date\nAAPL,10,150.0,2023-01-15"
        parsed = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(csv_bytes), "text/csv")},
        ).json()

        commit_payload = {
            "id": "primary",
            "name": parsed["name"],
            "holdings": [
                {
                    "ticker": h["ticker"],
                    "quantity": h["quantity"],
                    "cost_per_share": h["cost_per_share"],
                    "acquired": h["acquired"],
                }
                for h in parsed["holdings"]
            ],
        }
        r = upload_client.post("/api/portfolio", json=commit_payload)
        assert r.status_code == 200
        assert r.json() == {"portfolio_id": "primary"}
