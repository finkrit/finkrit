# finagent/tests/__init__.py
"""Tests for finagent — mirrors the package tree (agent/, report/, adapter/, store/).

No network and no live model: data comes from the fake HistoryProvider in
``fixtures.py``; the conversational path is driven by pydantic-ai's
``FunctionModel`` (scripted) or ``TestModel``, never a real backend.
"""
