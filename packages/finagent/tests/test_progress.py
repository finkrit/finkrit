# finagent/tests/test_progress.py
"""
Live progress steps off a real run.

Driven end to end through a scripted FunctionModel rather than by handing
synthetic events to the translator, because the thing worth guarding is that
finkrit's vocabulary lines up with what pydantic-ai actually emits, which a
hand built event cannot prove.
"""
from __future__ import annotations

import asyncio
import json
import warnings
from typing import AsyncIterator

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from finagent.assistant import Assistant
from finagent.progress import Step, StepDetail, StepKind, StepStatus, progress_handler
from finkritcore.store import InMemoryStore
from finkritcore.tests.fixtures import make_portfolio, make_registry

warnings.filterwarnings("ignore", message="Could not generate return schema")

# Setting an event handler puts pydantic-ai on its STREAMING request path, so
# these scripts are stream_functions (yielding deltas) rather than the plain
# FunctionModel callables the other suites use. That is not a test artifact:
# progress reporting is only possible on the streaming path, so exercising it
# is exercising the configuration a caller with a handler actually gets.


def _tool_call(index: int, name: str, args: dict) -> dict[int, DeltaToolCall]:
    return {index: DeltaToolCall(name=name, json_args=json.dumps(args), tool_call_id=f"call-{name}-{index}")}


def _answered(messages) -> bool:
    return any(
        isinstance(part, ToolReturnPart)
        for message in messages
        for part in getattr(message, "parts", [])
    )


# Every script branches on the tools it was handed, because the orchestrator and
# each nested specialist share this one model. Branching on message count instead
# would have a specialist (whose history is also one message deep) emit the
# orchestrator's delegations, which it has no tools for.
def _is_orchestrator(info) -> bool:
    return any(tool.name == "ask_risk" for tool in info.function_tools)


async def _fan_out(messages, info) -> AsyncIterator:
    """Orchestrator delegates to two specialists, each answering in text."""
    if not _is_orchestrator(info):
        yield "specialist answer"
    elif _answered(messages):
        yield "combined"
    else:
        yield _tool_call(0, "ask_risk", {"question": "vol"})
        yield _tool_call(1, "ask_tax", {"question": "harvest"})


async def _specialist_calls_a_tool(messages, info) -> AsyncIterator:
    """A single specialist that calls one domain tool, so a TOOL step appears."""
    if _answered(messages):
        yield "done"
    else:
        yield _tool_call(0, "portfolio_volatility", {"portfolio_id": "port-1"})


def _assistant(script, on_step, detail: StepDetail = StepDetail.SUMMARY) -> Assistant:
    store = InMemoryStore()
    store.register_portfolio(make_portfolio())
    return Assistant(
        model=FunctionModel(stream_function=script),
        store=store,
        registry=make_registry(),
        event_handler=progress_handler(on_step, detail),
    )


def _run(
    script,
    question: str = "how am I doing?",
    agent: str | None = None,
    detail: StepDetail = StepDetail.SUMMARY,
) -> list[Step]:
    steps: list[Step] = []
    _assistant(script, steps.append, detail).conversation(agent=agent).ask(question)
    return steps


class TestSpecialistSteps:

    def test_every_delegation_starts_and_finishes(self):
        steps = [s for s in _run(_fan_out) if s.kind is StepKind.SPECIALIST]

        # Starts arrive in the order the orchestrator issued the calls.
        assert [s.name for s in steps if s.status is StepStatus.STARTED] == ["risk", "tax"]
        # Finishes arrive in COMPLETION order, which a fan out does not
        # guarantee to match call order (both specialists run concurrently, so
        # the faster one reports first). A consumer must pair on call_id and
        # never assume the finishes mirror the starts.
        assert {s.name for s in steps if s.status is StepStatus.FINISHED} == {"risk", "tax"}

    def test_start_carries_the_sub_question(self):
        # The same sub-question conversation.py reports after the fact, only
        # available while the user is still waiting.
        steps = _run(_fan_out)
        started = [s for s in steps if s.kind is StepKind.SPECIALIST and s.status is StepStatus.STARTED]
        assert [s.detail for s in started] == ["vol", "harvest"]

    def test_finish_matches_its_start_by_call_id(self):
        # A fan out issues both calls before either returns, so position cannot
        # pair them and the id has to.
        steps = [s for s in _run(_fan_out) if s.kind is StepKind.SPECIALIST]
        started = {s.call_id: s.name for s in steps if s.status is StepStatus.STARTED}
        finished = {s.call_id: s.name for s in steps if s.status is StepStatus.FINISHED}
        assert started and started == finished

    def test_a_started_step_precedes_its_own_finish(self):
        # What kills the perceived hang: the pill lights before the work ends.
        steps = [s for s in _run(_fan_out) if s.kind is StepKind.SPECIALIST]
        for call_id in {s.call_id for s in steps}:
            statuses = [s.status for s in steps if s.call_id == call_id]
            assert statuses.index(StepStatus.STARTED) < statuses.index(StepStatus.FINISHED)


class TestToolSteps:

    def test_a_domain_tool_reports_as_a_tool_not_a_specialist(self):
        steps = _run(_specialist_calls_a_tool, agent="risk")
        assert [(s.kind, s.name, s.status) for s in steps] == [
            (StepKind.TOOL, "portfolio_volatility", StepStatus.STARTED),
            (StepKind.TOOL, "portfolio_volatility", StepStatus.FINISHED),
        ]

    def test_tool_steps_carry_no_sub_question(self):
        # detail is the orchestrator's sub-question, which a domain tool has not
        # got. Empty rather than a synthesized string.
        steps = _run(_specialist_calls_a_tool, agent="risk")
        assert all(s.detail == "" for s in steps)


class TestDetailLevel:
    """The off switch. SUMMARY must withhold at the source, not leave the
    consumer to filter, so a payload that was never wanted cannot end up in a
    log or a transcript by accident."""

    def test_summary_withholds_the_specialist_answer(self):
        finished = [
            s for s in _run(_fan_out)
            if s.kind is StepKind.SPECIALIST and s.status is StepStatus.FINISHED
        ]
        assert finished and all(s.content == "" for s in finished)

    def test_full_carries_the_specialist_answer(self):
        finished = [
            s for s in _run(_fan_out, detail=StepDetail.FULL)
            if s.kind is StepKind.SPECIALIST and s.status is StepStatus.FINISHED
        ]
        assert finished and all(s.content == "specialist answer" for s in finished)

    def test_summary_withholds_tool_arguments(self):
        started = [
            s for s in _run(_specialist_calls_a_tool, agent="risk")
            if s.status is StepStatus.STARTED
        ]
        assert started and all(s.args == {} for s in started)

    def test_full_carries_tool_arguments(self):
        started = [
            s for s in _run(_specialist_calls_a_tool, agent="risk", detail=StepDetail.FULL)
            if s.status is StepStatus.STARTED
        ]
        assert [s.args for s in started] == [{"portfolio_id": "port-1"}]

    def test_summary_is_the_default(self):
        # Carrying answers and parameters is always a decision someone made.
        steps: list[Step] = []
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        assistant = Assistant(
            model=FunctionModel(stream_function=_fan_out),
            store=store,
            registry=make_registry(),
            event_handler=progress_handler(steps.append),   # no detail argument
        )
        assistant.conversation().ask("anything")
        assert steps and all(s.content == "" and s.args == {} for s in steps)

    def test_a_delegation_keeps_its_sub_question_at_every_level(self):
        # The sub-question is what makes a pill legible, so it is carried at
        # SUMMARY too rather than being treated as heavy payload.
        for detail in (StepDetail.SUMMARY, StepDetail.FULL):
            started = [
                s for s in _run(_fan_out, detail=detail)
                if s.kind is StepKind.SPECIALIST and s.status is StepStatus.STARTED
            ]
            assert [s.detail for s in started] == ["vol", "harvest"]


class TestFailureIsolation:

    def test_a_raising_callback_does_not_fail_the_run(self):
        # Progress is a courtesy to the reader. A broken consumer must cost its
        # own output and nothing else, never the answer the user asked for.
        def explode(step: Step) -> None:
            raise RuntimeError("consumer is broken")

        assert _assistant(_fan_out, explode).conversation().ask("anything") == "combined"

    def test_no_handler_takes_the_non_streaming_path(self):
        # The default, and worth pinning: with no handler pydantic-ai issues a
        # plain request rather than a streamed one, so nothing about progress
        # reporting changes the cost or shape of an ordinary run.
        def plain(messages, info) -> ModelResponse:
            if not _is_orchestrator(info):
                return ModelResponse(parts=[TextPart("specialist answer")])
            if _answered(messages):
                return ModelResponse(parts=[TextPart("combined")])
            return ModelResponse(parts=[
                ToolCallPart(tool_name="ask_risk", args={"question": "vol"}),
                ToolCallPart(tool_name="ask_tax", args={"question": "harvest"}),
            ])

        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        assistant = Assistant(
            model=FunctionModel(plain), store=store, registry=make_registry()
        )
        assert assistant.conversation().ask("anything") == "combined"


class TestAsyncCallback:

    def test_an_async_callback_is_awaited(self):
        # A server pushing each step onto a websocket or an asyncio.Queue hands
        # in a coroutine function, which must be awaited rather than dropped.
        # asyncio.run rather than a plugin, matching the rest of the suite.
        steps: list[Step] = []

        async def collect(step: Step) -> None:
            steps.append(step)

        async def go() -> None:
            await _assistant(_fan_out, collect).conversation().ask_async("anything")

        asyncio.run(go())

        assert [s.name for s in steps if s.status is StepStatus.STARTED] == ["risk", "tax"]
