# finagent/tests/test_language.py
"""
The answer language reaches every agent.

The orchestrator combines specialist replies as they came back, so pinning it
alone is not enough: one specialist answering in another language is enough to
produce a bilingual reply. This asserts the setting lands on all five.
"""
from __future__ import annotations

import warnings

from finagent.agent.base import DEFAULT_LANGUAGE, with_language
from finagent.assistant import Assistant
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _instructions(agent) -> str:
    return "".join(agent.agent._instructions)


class TestAssistantThreadsLanguage:

    def _assistant(self, **kwargs) -> Assistant:
        return Assistant(
            model="test", store=InMemoryStore(), registry=make_registry(), **kwargs
        )

    def test_every_specialist_and_the_orchestrator_are_pinned(self):
        assistant = self._assistant(language="Thai")
        for agent in (
            assistant.risk,
            assistant.performance,
            assistant.optimization,
            assistant.tax,
            assistant.orchestrator,
        ):
            assert "Answer in Thai." in _instructions(agent)

    def test_english_without_asking(self):
        assistant = self._assistant()
        assert f"Answer in {DEFAULT_LANGUAGE}." in _instructions(assistant.risk)

    def test_each_agent_keeps_its_own_instructions(self):
        # The language is appended, it does not replace what makes a specialist
        # a specialist.
        assistant = self._assistant(language="Thai")
        assert "risk analyst" in _instructions(assistant.risk)
        assert "delegates to specialist tools" in _instructions(assistant.orchestrator)


class TestWithLanguage:

    def test_wraps_rather_than_replaces(self):
        assert "Original." in with_language("Original.")

    def test_brackets_the_instructions(self):
        # Both strong positions, because a directive only at the end was what
        # the orchestrator drifted past.
        text = with_language("Base.")
        assert text.index("Answer in English.") < text.index("Base.")
        assert text.index("Base.") < text.index("Your entire reply")
