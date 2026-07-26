# finkritserver/tests/test_app.py
from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic_ai.exceptions import UsageLimitExceeded

from finagent.assistant import Assistant
from finagent.store import PortfolioNotFoundError

from finkritserver.app import create_app


class _RaisingAssistant(Assistant):
    """An Assistant whose chat path always raises, to drive the /ask error
    branches. Constructed keyless (no model), route_async never reaches an LLM."""

    def __init__(self, exc: Exception) -> None:
        super().__init__()
        self._exc = exc

    async def route_async(self, question: str) -> str:
        raise self._exc


class TestHealth:
    def test_ok(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestRegisterPortfolio:
    def test_registers_and_returns_id(self, client: TestClient, portfolio_payload: dict):
        r = client.post("/api/portfolio", json=portfolio_payload)
        assert r.status_code == 200
        assert r.json() == {"portfolio_id": "port-1"}

    def test_omitted_id_defaults_to_primary(self, client: TestClient, portfolio_payload: dict):
        # Single-portfolio product: the frontend shouldn't have to invent an id.
        payload = {k: v for k, v in portfolio_payload.items() if k != "id"}
        r = client.post("/api/portfolio", json=payload)
        assert r.status_code == 200
        assert r.json() == {"portfolio_id": "primary"}

    def test_second_upload_overwrites_the_first(self, client: TestClient, portfolio_payload: dict):
        # No delete endpoint by design -- re-registering the same (default) id
        # replaces the previous portfolio.
        first = {k: v for k, v in portfolio_payload.items() if k != "id"}
        client.post("/api/portfolio", json=first)

        second = {**first, "name": "Replacement Portfolio"}
        r = client.post("/api/portfolio", json=second)
        assert r.status_code == 200

        report = client.get("/api/portfolio/primary/report").json()
        assert report["portfolio_id"] == "primary"

    def test_rejects_empty_holdings(self, client: TestClient):
        r = client.post("/api/portfolio", json={"id": "p", "name": "n", "holdings": []})
        assert r.status_code == 422  # pydantic min_length=1

    def test_rejects_non_positive_quantity(self, client: TestClient):
        bad = {
            "id": "p", "name": "n",
            "holdings": [{"ticker": "AAA", "quantity": 0, "cost_per_share": 100, "acquired": "2024-01-02"}],
        }
        assert client.post("/api/portfolio", json=bad).status_code == 422


class TestListPortfolios:
    def test_empty_by_default(self, client: TestClient):
        r = client.get("/api/portfolios")
        assert r.status_code == 200
        assert r.json() == []

    def test_lists_registered_portfolios(self, client: TestClient, portfolio_payload: dict):
        client.post("/api/portfolio", json=portfolio_payload)
        r = client.get("/api/portfolios")
        assert r.json() == [{"id": "port-1", "name": "Test Portfolio"}]


class TestReport:
    def _register(self, client: TestClient, payload: dict):
        assert client.post("/api/portfolio", json=payload).status_code == 200

    def test_core_report(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/report")  # defaults to core
        assert r.status_code == 200
        body = r.json()
        assert body["portfolio_id"] == "port-1"
        assert body["volatility"] is not None
        assert body["value_at_risk"] is not None
        assert body["beta"] is not None
        assert body["max_drawdown"] is not None
        assert body["variance"] is None  # not in core
        assert body["params"]["benchmark_ticker"] == "^GSPC"

    def test_all_report_has_contributions(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        body = client.get("/api/portfolio/port-1/report?metrics=all").json()
        assert set(body["marginal_contributions"]) == {"AAA", "BBB"}
        assert body["drawdown"]["periods"] > 0

    def test_unknown_portfolio_is_404(self, client: TestClient):
        r = client.get("/api/portfolio/nope/report")
        assert r.status_code == 404

    def test_bad_metric_selector_is_400(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/report?metrics=everything")
        assert r.status_code == 400

    def test_report_is_json_serializable_end_to_end(self, client: TestClient, portfolio_payload: dict):
        # Guards the dataclass -> JSON path (enums, dates, nested DrawdownSummary).
        self._register(client, portfolio_payload)
        body = client.get("/api/portfolio/port-1/report?metrics=all").json()
        assert body["params"]["var_method"] == "historical"     # enum -> value
        assert isinstance(body["params"]["confidence"], float)


class TestAsk:
    def test_ask_returns_an_answer(self, client: TestClient, portfolio_payload: dict):
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        r = client.post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 200
        assert "volatility" in r.json()["answer"].lower()

    def test_ask_rejects_empty_question(self, client: TestClient):
        assert client.post("/api/ask", json={"question": ""}).status_code == 422

    def test_ask_unknown_portfolio_is_404(self):
        # A portfolio or asset miss escaping the run maps to 404, not a 500.
        app = create_app(_RaisingAssistant(PortfolioNotFoundError("portfolio 'x' not found")), static_dir=None)
        r = TestClient(app).post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 404

    def test_ask_agent_failure_is_502(self):
        # An agent run failure (LLM/provider error, usage limit, exhausted retry)
        # maps to a clean 502 with a readable message, not a raw traceback.
        app = create_app(_RaisingAssistant(UsageLimitExceeded("request limit exceeded")), static_dir=None)
        r = TestClient(app).post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 502
        assert "could not complete" in r.json()["detail"]
