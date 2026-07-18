# finkritserver/tests/test_spa.py
"""
Tests for CORS and the built-SPA fallback serving added in app.py.

Uses a separate `spa_client` fixture pointed at a temp directory standing in
for a built Svelte app -- the default `client` fixture (no static_dir on
disk) exercises the "UI not built yet" path instead.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from finkritserver.app import create_app


@pytest.fixture
def built_ui(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<html><body>INDEX</body></html>")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('hi');")
    return tmp_path


@pytest.fixture
def spa_client(assistant, built_ui: Path) -> TestClient:
    return TestClient(create_app(assistant, static_dir=built_ui))


class TestCors:
    def test_preflight_allows_configured_dev_origin(self, client: TestClient):
        r = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_actual_request_carries_cors_header(self, client: TestClient):
        r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_unlisted_origin_not_granted(self, client: TestClient):
        r = client.get("/api/health", headers={"Origin": "http://evil.example.com"})
        assert "access-control-allow-origin" not in r.headers

    def test_custom_origins_override_default(self, assistant):
        app = create_app(assistant, cors_origins=("http://example.com",))
        c = TestClient(app)
        r = c.get("/api/health", headers={"Origin": "http://example.com"})
        assert r.headers["access-control-allow-origin"] == "http://example.com"


class TestSpaServing:
    def test_root_serves_index(self, spa_client: TestClient):
        r = spa_client.get("/")
        assert r.status_code == 200
        assert "INDEX" in r.text

    def test_real_asset_file_served_as_is(self, spa_client: TestClient):
        r = spa_client.get("/assets/app.js")
        assert r.status_code == 200
        assert "console.log" in r.text

    def test_unknown_client_route_falls_back_to_index(self, spa_client: TestClient):
        # The case StaticFiles(html=True) gets wrong: a client-side route with
        # no matching file on disk should still return the SPA shell.
        r = spa_client.get("/dashboard")
        assert r.status_code == 200
        assert "INDEX" in r.text

    def test_deeply_nested_unknown_route_also_falls_back(self, spa_client: TestClient):
        r = spa_client.get("/dashboard/portfolio/abc")
        assert r.status_code == 200
        assert "INDEX" in r.text

    def test_api_routes_take_priority_over_spa_fallback(self, spa_client: TestClient):
        r = spa_client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_path_traversal_does_not_escape_static_dir(self, spa_client: TestClient):
        # Must not read arbitrary files off disk -- falls back to index.html
        # (or 404), never serves the traversed path's contents.
        r = spa_client.get("/../../../../../../etc/passwd")
        assert r.status_code in (200, 404)
        assert "root:" not in r.text  # /etc/passwd contents never leaked

    def test_missing_ui_returns_clear_404_not_crash(self, client: TestClient):
        # Default client's static_dir doesn't exist on disk -- API still works
        # (proven by other tests), and a UI route fails clearly, not with a
        # framework traceback.
        r = client.get("/dashboard")
        assert r.status_code == 404
        assert "not built" in r.json()["detail"].lower()

    def test_static_dir_none_disables_spa_entirely(self, assistant):
        app = create_app(assistant, static_dir=None)
        c = TestClient(app)
        assert c.get("/api/health").status_code == 200
        assert c.get("/dashboard").status_code == 404
