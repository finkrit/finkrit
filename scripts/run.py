#!/usr/bin/env python3
"""
One command to run finkrit end to end: the FastAPI server (real LLM, real
market data) plus the frontend, with your browser opened for you.

    export LLM_API_KEY=sk-ant-...                 # or an OpenAI/Google/... key
    .finkritvenv/bin/python scripts/run.py                 # build once, serve
    .finkritvenv/bin/python scripts/run.py --dev           # Vite HMR, hot reload
    .finkritvenv/bin/python scripts/run.py --model openai:gpt-5.2
    .finkritvenv/bin/python scripts/run.py --no-browser --port 8001

Two ways to serve the UI:

    default   Build the SvelteKit app once and let FastAPI serve it, one
              origin on --port. Closest to production. Rebuild to see UI edits.
    --dev     Run the Vite dev server alongside the API so UI edits hot reload.
              Vite serves on 5173 and proxies /api to the FastAPI port. Use
              this while working on the frontend. Both processes stop together
              on Ctrl C.

--model is a pydantic-ai "provider:model_name" string (for example
anthropic:claude-sonnet-5, openai:gpt-5.2, google:gemini-3-pro). Any provider
pydantic-ai supports works, not only Anthropic.

One env var regardless of provider: LLM_API_KEY. pydantic-ai's providers each
default to reading their OWN var (ANTHROPIC_API_KEY, OPENAI_API_KEY, and so
on). We override the provider construction step (infer_model's
provider_factory hook) to inject LLM_API_KEY as that provider's api_key
instead, so switching --model does not mean switching which env var you export.
If LLM_API_KEY is unset, this falls back to each provider's normal default
lookup, so an existing ANTHROPIC_API_KEY or OPENAI_API_KEY still works.

Uses a real Assistant: live YFinance data (memoized per session, not
persistent, see finkritq/data/providers/memoizing.py), so chat and upload
genuinely call an LLM.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "apps" / "finkritweb"

# Vite's default dev port (see apps/finkritweb/vite.config.ts). The dev proxy
# there forwards /api to the FastAPI port, so the browser only ever talks to
# this one origin in --dev mode.
VITE_DEV_PORT = 5173

sys.path.insert(0, str(REPO_ROOT / "packages"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))


def resolve_model(model_string: str):
    """provider:model_name to a real pydantic-ai Model, authenticated from
    LLM_API_KEY if set (falling back to each provider's own default env var
    lookup otherwise)."""
    from pydantic_ai.models import infer_model
    from pydantic_ai.providers import infer_provider, infer_provider_class

    llm_key = os.environ.get("LLM_API_KEY") or os.environ.get("LLM_KEY")

    def provider_factory(provider_name: str):
        if llm_key is None:
            return infer_provider(provider_name)  # normal default lookup
        return infer_provider_class(provider_name)(api_key=llm_key)

    return infer_model(model_string, provider_factory=provider_factory)


def ensure_web_deps() -> None:
    # Install the web app's node_modules on first use, so running this script
    # on a fresh clone does not fail before the build or dev server starts.
    if (WEB_DIR / "node_modules").is_dir():
        return
    print(f"Installing web dependencies ({WEB_DIR})...")
    subprocess.run(["npm", "install"], cwd=WEB_DIR, check=True)


def build_frontend() -> None:
    ensure_web_deps()
    print(f"Building frontend ({WEB_DIR})...")
    subprocess.run(["npm", "run", "build"], cwd=WEB_DIR, check=True)


def start_vite_dev() -> subprocess.Popen:
    """Start the Vite dev server in its own process group, so we can stop it
    (and the esbuild/vite children it spawns) cleanly when the API exits."""
    ensure_web_deps()
    print(f"Starting Vite dev server on port {VITE_DEV_PORT} (hot reload)...")
    return subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(VITE_DEV_PORT), "--strictPort"],
        cwd=WEB_DIR,
        start_new_session=True,
    )


def stop_process_group(proc: subprocess.Popen) -> None:
    # Signal the whole group so vite's child processes go down with it.
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass


def open_browser_when_ready(url: str) -> None:
    # Poll /api/health so we only open once the backend answers. In --dev this
    # also waits for Vite's proxy to be up, since the request goes through it.
    import urllib.request

    for _ in range(60):
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=0.5)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)
    print(f"Server did not come up in time. Open {url} manually.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", default="openai:gpt-5", help="pydantic-ai model string")
    parser.add_argument("--port", type=int, default=8000, help="FastAPI port")
    parser.add_argument("--dev", action="store_true", help="Vite dev server with hot reload")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-build", action="store_true", help="reuse the existing build (ignored with --dev)")
    args = parser.parse_args()

    if not (os.environ.get("LLM_API_KEY") or os.environ.get("LLM_KEY")):
        print(
            "Heads up: LLM_API_KEY is not set, falling back to each provider's own "
            "default env var (for example ANTHROPIC_API_KEY). Set LLM_API_KEY to use "
            "one var regardless of the --model provider.\n"
            "(Dashboard and report still work without any key. Only upload and chat "
            "need an LLM.)\n"
        )

    # In --dev the browser opens the Vite origin (hot reload), which proxies
    # /api to FastAPI. Otherwise FastAPI serves the built UI on its own port.
    browse_url = f"http://localhost:{VITE_DEV_PORT}" if args.dev else f"http://127.0.0.1:{args.port}"

    vite: subprocess.Popen | None = None
    if args.dev:
        vite = start_vite_dev()
    elif not args.skip_build:
        build_frontend()

    from finagent.assistant import Assistant
    from finkritserver.app import create_app

    model = resolve_model(args.model)
    assistant = Assistant(model=model)  # real registry (YFinance) + real store
    # In --dev Vite serves the UI, so the API does not need to (and should not,
    # the build may be stale). static_dir=None runs the API bare.
    app = create_app(assistant, static_dir=None) if args.dev else create_app(assistant)

    if not args.no_browser:
        threading.Thread(target=open_browser_when_ready, args=(browse_url,), daemon=True).start()

    mode = "dev, hot reload" if args.dev else "built UI"
    print(f"\nfinkrit running at {browse_url}  (model: {args.model}, {mode})\n")

    import uvicorn

    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    finally:
        if vite is not None:
            stop_process_group(vite)


if __name__ == "__main__":
    main()
