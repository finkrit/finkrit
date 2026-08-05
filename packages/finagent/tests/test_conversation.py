# finagent/tests/test_conversation.py
"""
Tests for threaded, multi-turn conversations.

The behavior that matters is that turn N sees turns 1..N-1, and that trimming a
long thread never separates a tool call from its result, which would hand the
model a tool return it never asked for.
"""
from __future__ import annotations

import warnings

from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from finagent.assistant import Assistant
from finagent.conversation import Conversation, trim_to_turns
from finkritcore.store import InMemoryStore
from finkritcore.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")


def _count_user_prompts(messages) -> int:
    return sum(
        1
        for message in messages
        for part in getattr(message, "parts", [])
        if isinstance(part, UserPromptPart)
    )


def _echo_visible_turns(messages, info) -> ModelResponse:
    """Answers with how many user prompts it can see, which is the thread depth."""
    return ModelResponse(parts=[TextPart(str(_count_user_prompts(messages)))])


def _always_calls_a_tool(messages, info) -> ModelResponse:
    """One tool call per turn, so history accumulates call/return pairs."""
    last = messages[-1]
    if any(isinstance(part, ToolReturnPart) for part in getattr(last, "parts", [])):
        return ModelResponse(parts=[TextPart("done")])
    return ModelResponse(
        parts=[ToolCallPart(tool_name="portfolio_volatility", args={"portfolio_id": "port-1"})]
    )


def _assistant(script) -> Assistant:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return Assistant(model=FunctionModel(script), store=store, registry=make_registry())


class TestThreading:

    def test_each_turn_sees_the_previous_ones(self):
        chat = _assistant(_echo_visible_turns).conversation()
        assert chat.ask("first") == "1"
        assert chat.ask("second") == "2"
        assert chat.ask("third") == "3"

    def test_turns_counts_user_questions(self):
        chat = _assistant(_echo_visible_turns).conversation()
        chat.ask("one")
        chat.ask("two")
        assert chat.turns == 2

    def test_reset_drops_the_history(self):
        chat = _assistant(_echo_visible_turns).conversation()
        chat.ask("one")
        chat.ask("two")
        chat.reset()
        assert chat.turns == 0
        assert chat.ask("fresh") == "1"

    def test_separate_conversations_do_not_share_history(self):
        assistant = _assistant(_echo_visible_turns)
        first, second = assistant.conversation(), assistant.conversation()
        first.ask("a")
        first.ask("b")
        assert second.ask("c") == "1"

    def test_messages_property_is_a_copy(self):
        chat = _assistant(_echo_visible_turns).conversation()
        chat.ask("one")
        snapshot = chat.messages
        snapshot.clear()
        assert chat.turns == 1

    def test_a_named_specialist_can_be_threaded(self):
        chat = _assistant(_echo_visible_turns).conversation(agent="risk")
        chat.ask("one")
        assert chat.ask("two") == "2"


class TestSpecialistsReported:
    """The UI shows which specialists answered, so the fan out is visible rather
    than implied. That list comes from the tools the orchestrator actually
    called, not from anything the model says."""

    @staticmethod
    def _fan_out(messages, info) -> ModelResponse:
        tools = {tool.name for tool in info.function_tools}
        # Only the last message, since a threaded turn carries the previous
        # turn's tool returns in its history and would short circuit on those.
        answered = any(
            isinstance(part, ToolReturnPart)
            for part in getattr(messages[-1], "parts", [])
        )
        if answered:
            return ModelResponse(parts=[TextPart("combined")])
        if "ask_risk" in tools:
            return ModelResponse(parts=[
                ToolCallPart(tool_name="ask_risk", args={"question": "vol"}),
                ToolCallPart(tool_name="ask_tax", args={"question": "harvest"}),
            ])
        return ModelResponse(parts=[TextPart("specialist answer")])

    def test_reports_the_specialists_in_call_order(self):
        chat = _assistant(self._fan_out).conversation()
        chat.ask("volatility and harvesting please")
        assert chat.last_specialist_names == ["risk", "tax"]

    def test_is_empty_when_a_specialist_is_threaded_directly(self):
        # No orchestrator means no fan out to report.
        chat = _assistant(_echo_visible_turns).conversation(agent="risk")
        chat.ask("volatility")
        assert chat.last_specialists == []
        assert chat.last_specialist_names == []

    def test_resets_between_turns(self):
        chat = _assistant(self._fan_out).conversation()
        chat.ask("first")
        assert chat.last_specialist_names == ["risk", "tax"]
        # The second turn's list must describe that turn, not accumulate.
        chat.ask("second")
        assert chat.last_specialist_names == ["risk", "tax"]

    def test_carries_each_specialist_sub_question_and_answer(self):
        # The point of showing the work: the reply the specialist actually gave,
        # paired with the sub-question it was handed, so a user can check the
        # combined answer against it rather than trust it.
        chat = _assistant(self._fan_out).conversation()
        chat.ask("volatility and harvesting please")

        assert [(s.name, s.question) for s in chat.last_specialists] == [
            ("risk", "vol"), ("tax", "harvest"),
        ]
        assert all(s.answer for s in chat.last_specialists)

    def test_a_specialist_called_twice_is_one_pill_but_two_answers(self):
        # Two sub-questions to one specialist are two different answers worth
        # reading, and one name worth showing.
        def twice(messages, info):
            if len(messages) == 1:
                return ModelResponse(parts=[
                    ToolCallPart(tool_name="ask_risk", args={"question": "vol"}),
                    ToolCallPart(tool_name="ask_risk", args={"question": "drawdown"}),
                ])
            return ModelResponse(parts=[TextPart("combined")])

        chat = _assistant(twice).conversation()
        chat.ask("volatility and drawdown")

        assert chat.last_specialist_names == ["risk"]
        assert [s.question for s in chat.last_specialists] == ["vol", "drawdown"]


class TestTrimming:

    def test_thread_is_capped_at_max_turns(self):
        chat = _assistant(_echo_visible_turns).conversation(max_turns=2)
        for i in range(5):
            chat.ask(f"question {i}")
        assert chat.turns == 2

    def test_trimming_keeps_tool_calls_with_their_returns(self):
        # Cutting mid-turn would orphan a ToolReturnPart from its ToolCallPart.
        chat = _assistant(_always_calls_a_tool).conversation(agent="risk", max_turns=2)
        for i in range(5):
            chat.ask(f"question {i}")

        call_ids, return_ids = [], []
        for message in chat.messages:
            for part in getattr(message, "parts", []):
                if isinstance(part, ToolCallPart):
                    call_ids.append(part.tool_call_id)
                if isinstance(part, ToolReturnPart):
                    return_ids.append(part.tool_call_id)

        assert return_ids, "expected the scripted model to have called a tool"
        assert all(rid in call_ids for rid in return_ids)

    def test_trimmed_history_starts_at_a_user_turn(self):
        chat = _assistant(_always_calls_a_tool).conversation(agent="risk", max_turns=2)
        for i in range(4):
            chat.ask(f"question {i}")
        first = chat.messages[0]
        assert any(isinstance(p, UserPromptPart) for p in getattr(first, "parts", []))

    def test_trim_to_turns_is_a_no_op_below_the_cap(self):
        chat = _assistant(_echo_visible_turns).conversation()
        chat.ask("one")
        messages = chat.messages
        assert trim_to_turns(messages, 10) == messages

    def test_zero_turns_keeps_nothing(self):
        chat = _assistant(_echo_visible_turns).conversation()
        chat.ask("one")
        assert trim_to_turns(chat.messages, 0) == []
