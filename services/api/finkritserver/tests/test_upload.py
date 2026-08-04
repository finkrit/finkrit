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


# A header naming only two of the four fields, so there is genuine ambiguity
# and the upload falls through to the model. A file naming all four is read in
# code and never reaches one, which is what TestUploadWithoutAModel covers.
_AMBIGUOUS_CSV = b"Symbol,Shares\nAAPL,10"

# All four fields under names the alias table knows, so this is answered
# without a model.
_COMPLETE_CSV = b"Symbol,Shares,Cost,Date\nAAPL,10,150.0,2023-01-15"


class TestUploadPortfolio:
    """The model fallback, reached only by a file we cannot read in code."""

    def test_parses_csv_and_returns_parsed_portfolio(self, upload_client: TestClient):
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(_AMBIGUOUS_CSV), "text/csv")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Uploaded Portfolio"
        assert body["holdings"][0]["ticker"] == "AAPL"

    def test_surfaces_warnings_for_user_review(self, upload_client: TestClient):
        r = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(_AMBIGUOUS_CSV), "text/csv")},
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
        parsed = upload_client.post(
            "/api/portfolio/upload",
            files={"file": ("holdings.csv", io.BytesIO(_COMPLETE_CSV), "text/csv")},
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


class TestUploadWithoutAModel:
    """A file whose header names all four fields is read in code.

    Worth its own fixture with no model at all: if anything on this path still
    reaches for one, these fail loudly rather than quietly costing a round trip
    that a user on a local model waits minutes for.
    """

    @pytest.fixture
    def keyless_client(self) -> TestClient:
        assistant = Assistant(store=InMemoryStore(), registry=make_registry())
        return TestClient(create_app(assistant, static_dir=None))

    def _upload(self, client: TestClient, body: bytes, filename: str = "holdings.csv"):
        return client.post(
            "/api/portfolio/upload",
            files={"file": (filename, io.BytesIO(body), "text/csv")},
        )

    def test_a_complete_header_needs_no_model(self, keyless_client: TestClient):
        r = self._upload(keyless_client, _COMPLETE_CSV)
        assert r.status_code == 200
        holding = r.json()["holdings"][0]
        assert holding["ticker"] == "AAPL"
        assert holding["quantity"] == 10
        assert holding["cost_per_share"] == 150.0
        assert holding["acquired"] == "2023-01-15"

    def test_it_is_named_after_the_file(self, keyless_client: TestClient):
        # The model names a portfolio from its contents. Without one, the
        # filename is the only thing the user will recognize.
        r = self._upload(keyless_client, _COMPLETE_CSV, filename="schwab-export.csv")
        assert r.json()["name"] == "schwab-export"

    def test_an_ambiguous_header_still_needs_one(self, keyless_client: TestClient):
        # Falls through to the model, and there is none, so this must fail
        # rather than silently inventing the missing columns. The endpoint has
        # no handler for it, so the error reaches the caller raw. Pinned as it
        # is rather than as it should be: the upload path's error mapping is a
        # gap of its own, and a test claiming a 500 here would hide it.
        with pytest.raises(RuntimeError, match="could not be read without one"):
            self._upload(keyless_client, _AMBIGUOUS_CSV)

    def test_money_formatting_survives(self, keyless_client: TestClient):
        # What a real export actually writes, and the reason this path exists
        # rather than str() on the raw cell.
        body = b'Symbol,Shares,Cost Per Share,Date Acquired\nAAPL,"1,000",$120.40,05/12/2021'
        holding = self._upload(keyless_client, body).json()["holdings"][0]
        assert holding["quantity"] == 1000
        assert holding["cost_per_share"] == 120.40
        assert holding["acquired"] == "2021-05-12"

    def test_repeated_tickers_stay_separate_lots(self, keyless_client: TestClient):
        # One row is one lot. Merging them would destroy what the tax
        # analytics choose between.
        body = (
            b"Symbol,Shares,Cost,Date\n"
            b"AAPL,10,150.0,2023-01-15\n"
            b"AAPL,5,180.0,2024-03-09"
        )
        holdings = self._upload(keyless_client, body).json()["holdings"]
        assert len(holdings) == 2
        assert [h["acquired"] for h in holdings] == ["2023-01-15", "2024-03-09"]
