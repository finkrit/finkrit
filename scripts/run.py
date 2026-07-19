#!/usr/bin/env python3
"""
Build the frontend, start the real server (real LLM, real market data), and
open your browser. This is what `finkrit chat` (private/webapp_plan.md
Phase 2) will eventually be -- for now, run it directly:

    export LLM_KEY=sk-ant-...                    # or an OpenAI/Google/... key
    .finkritvenv/bin/python scripts/run.py
    .finkritvenv/bin/python scripts/run.py --model openai:gpt-5.2
    .finkritvenv/bin/python scripts/run.py --no-browser --port 8001

--model is a pydantic-ai "provider:model_name" string (e.g.
anthropic:claude-sonnet-5, openai:gpt-5.2, google:gemini-3-pro) -- any
provider pydantic-ai supports works, not just Anthropic.

One env var regardless of provider: LLM_KEY. pydantic-ai's providers each
default to reading their OWN var (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...);
we override the provider-construction step (infer_model's provider_factory
hook) to inject LLM_KEY as that provider's api_key instead, so switching
--model doesn't mean switching which env var you export. If LLM_KEY isn't
set, this falls back to each provider's normal default lookup, so an
existing ANTHROPIC_API_KEY/OPENAI_API_KEY still works unchanged.

Uses a *real* Assistant: live YFinance data (memoized per session, not
persistent -- see finkritq/data/providers/memoizing.py), so chat/upload
genuinely call an LLM.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "apps" / "finkritweb"

sys.path.insert(0, str(REPO_ROOT / "packages"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))


def resolve_model(model_string: str):
    """provider:model_name -> a real pydantic-ai Model, authenticated from
    LLM_KEY if set (falling back to each provider's own default env var
    lookup otherwise)."""
    from pydantic_ai.models import infer_model
    from pydantic_ai.providers import infer_provider, infer_provider_class

    llm_key = os.environ.get("LLM_KEY")

    def provider_factory(provider_name: str):
        if llm_key is None:
            return infer_provider(provider_name)  # normal default lookup
        return infer_provider_class(provider_name)(api_key=llm_key)

    return infer_model(model_string, provider_factory=provider_factory)


def build_frontend() -> None:
    print(f"Building frontend ({WEB_DIR})...")
    subprocess.run(["npm", "run", "build"], cwd=WEB_DIR, check=True)


def open_browser_when_ready(url: str) -> None:
    import urllib.request

    for _ in range(60):
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=0.5)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)
    print(f"Server didn't come up in time -- open {url} manually.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="anthropic:claude-sonnet-5", help="pydantic-ai model string")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-build", action="store_true", help="reuse the existing build")
    args = parser.parse_args()

    if not os.environ.get("LLM_KEY"):
        print(
            "Heads up: LLM_KEY isn't set -- falling back to each provider's own default "
            "env var (e.g. ANTHROPIC_API_KEY). Set LLM_KEY to use one var regardless of "
            "--model's provider.\n"
            "(Dashboard/report still works without any key -- only upload/chat need an LLM.)\n"
        )

    if not args.skip_build:
        build_frontend()

    from finagent.assistant import Assistant
    from finkritserver.app import create_app

    model = resolve_model(args.model)
    assistant = Assistant(model=model)  # real registry (YFinance) + real store
    app = create_app(assistant)

    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    print(f"\nfinkrit running at {url}  (model: {args.model})\n")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
