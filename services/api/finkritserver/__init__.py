# finkritserver/__init__.py
"""
finkritserver — the FastAPI layer over a finagent Assistant.

Deliberately NOT part of finagent: finagent stays a pure, pip-installable
library, and the web/HTTP concern lives here. This package is where the future
RIA service will later add auth, sessions, and persistence -- keeping that out
of finagent preserves the "just pip install and ask" property.

  - ``app`` — ``create_app(assistant)`` factory returning a FastAPI app with the
    JSON API (health / portfolio registration / deterministic report / ask).
  - ``schemas`` — pydantic request/response models (the HTTP boundary types).
  - ``portfolio`` — builds a finkritq Portfolio from a flat PortfolioSpec.

Phase 1 is the API only; the built Svelte UI gets served from here later, and a
``finkrit chat`` CLI (separate meta-package) will spin it up. See
private/webapp_plan.md.
"""

from finkritserver.app import create_app

__all__ = ["create_app"]
