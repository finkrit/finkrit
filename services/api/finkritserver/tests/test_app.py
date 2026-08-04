# finkritserver/tests/test_app.py
from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic_ai.exceptions import UsageLimitExceeded

from finagent.assistant import Assistant
from finagent.store import PortfolioNotFoundError

from finkritserver.app import create_app


class _RaisingConversation:
    """Stands in for a threaded conversation and always fails."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def ask_async(self, question: str) -> str:
        raise self._exc


class _RaisingAssistant(Assistant):
    """An Assistant whose chat path always raises, to drive the /ask error
    branches. Constructed keyless (no model), so nothing reaches an LLM. The
    endpoint asks through a Conversation, so that is what is stubbed."""

    def __init__(self, exc: Exception) -> None:
        super().__init__()
        self._exc = exc

    def conversation(self, agent=None, max_turns=None):  # noqa: ARG002 - signature match
        return _RaisingConversation(self._exc)


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


class TestAskStream:
    """The same answer as /api/ask, delivered as a stream so the fan out is
    visible while it happens."""

    def _frames(self, body: str) -> list[dict]:
        import json

        return [
            json.loads(line[len("data: "):])
            for line in body.split("\n")
            if line.startswith("data: ")
        ]

    def _ask(self, client: TestClient, question: str = "What's my volatility?"):
        return client.post("/api/ask/stream", json={"question": question})

    def test_steps_arrive_before_the_answer(self, client: TestClient, portfolio_payload: dict):
        # The whole point: something to show while the run is still going.
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        r = self._ask(client)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")

        frames = self._frames(r.text)
        assert frames[-1]["type"] == "answer"
        assert all(f["type"] == "step" for f in frames[:-1])
        assert any(f["kind"] == "specialist" and f["name"] == "risk" for f in frames[:-1])

    def test_the_answer_frame_matches_the_plain_endpoint(self, client: TestClient, portfolio_payload: dict):
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        answer = self._frames(self._ask(client).text)[-1]
        assert "volatility" in answer["answer"].lower()
        assert answer["specialists"] == ["risk"]
        assert answer["conversation_id"]

    def test_a_failure_is_a_frame_not_a_status(self, client: TestClient):
        # The status line is spent by the time the run raises, so a client has
        # to read the stream to learn the question failed.
        r = self._ask(client)   # no portfolio registered
        assert r.status_code == 200
        assert self._frames(r.text)[-1]["type"] == "error"


class TestPrefetch:
    def _register(self, client: TestClient, payload: dict):
        assert client.post("/api/portfolio", json=payload).status_code == 200

    def _events(self, body: str) -> list[dict]:
        import json

        return [
            json.loads(line[len("data: "):])
            for line in body.split("\n")
            if line.startswith("data: ")
        ]

    def test_streams_start_per_ticker_and_end(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/prefetch")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")

        events = self._events(r.text)
        assert events[0]["event"] == "start"
        assert set(events[0]["tickers"]) == {"AAA", "BBB", "^GSPC"}
        assert events[-1] == {"event": "end"}
        done = {e["ticker"]: e["status"] for e in events[1:-1]}
        assert done == {"AAA": "ready", "BBB": "ready", "^GSPC": "ready"}

    def test_unknown_portfolio_is_404_not_a_stream(self, client: TestClient):
        assert client.get("/api/portfolio/nope/prefetch").status_code == 404


class TestTaxSignals:
    def _register(self, client: TestClient, payload: dict):
        assert client.post("/api/portfolio", json=payload).status_code == 200

    def test_signals_shape(self, client: TestClient, portfolio_payload: dict):
        # Content depends on fixture prices, so assert the contract: every
        # signal family present, rates echoed, JSON all the way out.
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/tax/signals")
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {
            "as_of", "short_term_rate", "long_term_rate",
            "total_harvestable_loss", "estimated_harvest_saving",
            "harvest", "wash_sale_blocked", "countdowns",
        }
        assert body["short_term_rate"] == 0.3
        assert body["long_term_rate"] == 0.15

    def test_rates_are_query_params(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        body = client.get(
            "/api/portfolio/port-1/tax/signals?short_term_rate=0.35&long_term_rate=0.2"
        ).json()
        assert body["short_term_rate"] == 0.35
        assert body["long_term_rate"] == 0.2

    def test_inverted_rates_are_400(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get(
            "/api/portfolio/port-1/tax/signals?short_term_rate=0.1&long_term_rate=0.2"
        )
        assert r.status_code == 400

    def test_unknown_portfolio_is_404(self, client: TestClient):
        assert client.get("/api/portfolio/nope/tax/signals").status_code == 404


class TestRebalanceCompare:
    def _register(self, client: TestClient, payload: dict):
        assert client.post("/api/portfolio", json=payload).status_code == 200

    def test_compare_returns_the_fixed_strategy_menu(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/rebalance/compare")
        assert r.status_code == 200
        body = r.json()
        # The menu is fixed in code; the card renders exactly these rows.
        assert set(body["strategies"]) == {"full", "band_edge", "partial_fill"}
        for plan in body["strategies"].values():
            assert set(plan) >= {
                "sells", "deferred", "realized_gain", "harvested_loss", "residual_drift",
            }
        assert body["objective"] == "min_variance"
        assert "target_weights" in body

    def test_gain_budget_passes_through(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        body = client.get(
            "/api/portfolio/port-1/rebalance/compare?gain_budget=500"
        ).json()
        assert body["gain_budget"] == 500.0

    def test_unknown_objective_is_400(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/rebalance/compare?objective=moon")
        assert r.status_code == 400

    def test_unknown_lot_method_is_400(self, client: TestClient, portfolio_payload: dict):
        self._register(client, portfolio_payload)
        r = client.get("/api/portfolio/port-1/rebalance/compare?method=yolo")
        assert r.status_code == 400
        assert "hifo" in r.json()["detail"]

    def test_unknown_portfolio_is_404(self, client: TestClient):
        assert client.get("/api/portfolio/nope/rebalance/compare").status_code == 404


class TestAsk:
    def test_ask_returns_an_answer(self, client: TestClient, portfolio_payload: dict):
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        r = client.post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 200
        assert "volatility" in r.json()["answer"].lower()

    def test_ask_reports_which_specialists_answered(self, client: TestClient, portfolio_payload: dict):
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        body = client.post("/api/ask", json={"question": "What's my volatility?"}).json()
        assert body["specialists"] == ["risk"]

    def test_ask_carries_each_specialist_verbatim_answer(self, client: TestClient, portfolio_payload: dict):
        # Showing the work: the UI opens a pill onto what that specialist
        # actually returned, so it has to survive the whole way out to JSON and
        # not just exist on the Conversation.
        assert client.post("/api/portfolio", json=portfolio_payload).status_code == 200
        body = client.post("/api/ask", json={"question": "What's my volatility?"}).json()

        fan_out = body["specialist_answers"]
        assert [s["name"] for s in fan_out] == ["risk"]
        assert fan_out[0]["question"] == "What is the volatility?"
        assert fan_out[0]["answer"], "the specialist's own reply must not be empty"

    def test_ask_rejects_empty_question(self, client: TestClient):
        assert client.post("/api/ask", json={"question": ""}).status_code == 422

    def test_ask_unknown_portfolio_is_404(self):
        # A portfolio or asset miss escaping the run maps to 404, not a 500.
        app = create_app(_RaisingAssistant(PortfolioNotFoundError("portfolio 'x' not found")), static_dir=None)
        r = TestClient(app).post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 404

    def test_ask_issues_a_conversation_id(self, client: TestClient, portfolio_payload: dict):
        client.post("/api/portfolio", json=portfolio_payload)
        body = client.post("/api/ask", json={"question": "What's my volatility?"}).json()
        assert body["conversation_id"]

    def test_same_conversation_id_keeps_the_thread(self, client: TestClient, portfolio_payload: dict):
        # The point of the feature: a follow-up must arrive with the prior turns.
        client.post("/api/portfolio", json=portfolio_payload)
        first = client.post("/api/ask", json={"question": "What's my volatility?"}).json()
        cid = first["conversation_id"]
        second = client.post(
            "/api/ask", json={"question": "and my drawdown?", "conversation_id": cid}
        ).json()
        assert second["conversation_id"] == cid

    def test_omitting_the_id_starts_a_separate_thread(self, client: TestClient, portfolio_payload: dict):
        client.post("/api/portfolio", json=portfolio_payload)
        first = client.post("/api/ask", json={"question": "What's my volatility?"}).json()
        second = client.post("/api/ask", json={"question": "What's my volatility?"}).json()
        assert first["conversation_id"] != second["conversation_id"]

    def test_reset_forgets_the_thread(self, client: TestClient, portfolio_payload: dict):
        client.post("/api/portfolio", json=portfolio_payload)
        cid = client.post("/api/ask", json={"question": "What's my volatility?"}).json()[
            "conversation_id"
        ]
        assert client.post(f"/api/ask/{cid}/reset").status_code == 204

    def test_reset_of_an_unknown_id_is_a_no_op(self, client: TestClient):
        # The desired end state (no history under that id) already holds.
        assert client.post("/api/ask/does-not-exist/reset").status_code == 204

    def test_ask_agent_failure_is_502(self):
        # An agent run failure (LLM/provider error, usage limit, exhausted retry)
        # maps to a clean 502 with a readable message, not a raw traceback.
        app = create_app(_RaisingAssistant(UsageLimitExceeded("request limit exceeded")), static_dir=None)
        r = TestClient(app).post("/api/ask", json={"question": "What's my volatility?"})
        assert r.status_code == 502
        assert "could not complete" in r.json()["detail"]
