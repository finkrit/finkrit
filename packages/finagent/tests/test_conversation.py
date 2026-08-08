# finagent/tests/test_conversation.py
"""
Tests for threaded, multi-turn conversations.

The behavior that matters is that turn N sees turns 1..N-1, and that trimming a
long thread never separates a tool call from its result, which would hand the
model a tool return it never asked for.
"""
from __future__ import annotations

import warnings

from types import SimpleNamespace

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from finagent.assistant import Assistant
from finagent.conversation import Conversation, answer_of, trim_to_turns
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
        parts=[ToolCallPart(tool_name="portfolio_risk", args={"portfolio_id": "port-1"})]
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


class TestSingleSpecialistPassthrough:
    """When one specialist answered there is nothing to combine, so the
    orchestrator's closing text is a second generation over content it was told
    not to alter. Both failures observed on a local model took that shape: a
    beta restated as -0.05 where the specialist said -0.06, and a specialist
    answering in Chinese followed by an orchestrator replying in Thai."""

    def _result(self, specialist_answers: list[tuple[str, str]], synthesis: str,
                history: list | None = None):
        # One ask_* call per entry, each with its return, then the
        # orchestrator's own closing text. `history` is prior turns, which
        # all_messages() carries and new_messages() does not.
        messages: list = []
        for index, (tool, answer) in enumerate(specialist_answers):
            call_id = f"call-{index}"
            messages.append(ModelResponse(parts=[ToolCallPart(
                tool_name=tool, args={"question": "q"}, tool_call_id=call_id)]))
            messages.append(ModelRequest(parts=[ToolReturnPart(
                tool_name=tool, content=answer, tool_call_id=call_id)]))
        return SimpleNamespace(
            all_messages=lambda: (history or []) + messages,
            new_messages=lambda: messages,
            output=synthesis,
        )

    def test_one_specialist_answer_is_passed_through_verbatim(self):
        result = self._result([("ask_risk", "Portfolio beta is -0.06.")],
                              synthesis="Portfolio beta is -0.05.")
        assert answer_of(result) == "Portfolio beta is -0.06."

    def test_the_rewrite_that_changed_a_number_can_no_longer_reach_a_user(self):
        # The exact regression. -0.06 is what was computed; -0.05 is what the
        # orchestrator wrote when asked to restate it.
        result = self._result([("ask_risk", "PG beta -0.06")], synthesis="PG beta -0.05")
        assert "-0.06" in answer_of(result)
        assert "-0.05" not in answer_of(result)

    def test_a_drifting_language_rewrite_cannot_reach_a_user_either(self):
        # A specialist answering in one language and the orchestrator in a
        # third is a cascade this removes for the single specialist case.
        result = self._result([("ask_risk", "Beta is 0.76.")], synthesis="เบต้าคือ 0.76")
        assert answer_of(result) == "Beta is 0.76."

    def test_a_fan_out_still_gets_combined(self):
        # Two specialists genuinely need combining, so synthesis is the answer.
        result = self._result(
            [("ask_risk", "Volatility 25%."), ("ask_tax", "Harvestable $4,180.")],
            synthesis="Volatility is 25% and $4,180 is harvestable.",
        )
        assert answer_of(result) == "Volatility is 25% and $4,180 is harvestable."

    def test_a_run_with_no_specialist_falls_through(self):
        # A plain CapabilityAgent delegates to nobody, so its own text is the
        # only answer there is.
        result = self._result([], synthesis="Volatility is 25%.")
        assert answer_of(result) == "Volatility is 25%."

    def test_an_empty_specialist_answer_falls_through(self):
        # Passing through nothing would turn a thin answer into no answer.
        result = self._result([("ask_risk", "   ")], synthesis="I could not compute that.")
        assert answer_of(result) == "I could not compute that."


class TestFollowUpTurnsAreNotTheFirstTurn:
    """The bug this class exists for: answer_of read all_messages(), which in a
    threaded conversation carries every prior turn. Turn two found turn one's
    specialist call, counted exactly one, and returned turn one's answer. Every
    follow up repeated the first reply verbatim.

    Invisible until the CLI started threading, because until then each question
    was a fresh run and all_messages() equalled new_messages()."""

    def _turn(self, tool: str | None, answer: str, synthesis: str, history: list):
        messages: list = []
        if tool is not None:
            messages.append(ModelResponse(parts=[ToolCallPart(
                tool_name=tool, args={"question": "q"}, tool_call_id="c")]))
            messages.append(ModelRequest(parts=[ToolReturnPart(
                tool_name=tool, content=answer, tool_call_id="c")]))
        return SimpleNamespace(
            all_messages=lambda: history + messages,
            new_messages=lambda: messages,
            output=synthesis,
        )

    def test_a_second_turn_that_called_nobody_uses_its_own_answer(self):
        # The exact failure: turn one delegated, turn two did not, and turn two
        # was handed turn one's reply.
        first = self._turn("ask_risk", "Betas: AAPL 0.76.", "ignored", history=[])
        prior = first.all_messages()
        second = self._turn(None, "", "I cannot convert those to dollars.", history=prior)
        assert answer_of(second) == "I cannot convert those to dollars."

    def test_a_second_turn_that_did_delegate_uses_its_own_specialist(self):
        first = self._turn("ask_risk", "Betas: AAPL 0.76.", "ignored", history=[])
        second = self._turn("ask_tax", "Harvestable: $4,180.", "rewritten",
                            history=first.all_messages())
        assert answer_of(second) == "Harvestable: $4,180."

    def test_history_length_never_changes_the_answer(self):
        # Ten turns of accumulated history must not make turn eleven look like
        # a fan out and fall through to synthesis.
        history: list = []
        for _ in range(10):
            turn = self._turn("ask_risk", "old", "old", history=history)
            history = turn.all_messages()
        latest = self._turn("ask_risk", "the current answer", "rewritten", history=history)
        assert answer_of(latest) == "the current answer"
