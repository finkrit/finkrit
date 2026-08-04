# finagent/progress.py
"""
Live progress for a run, in finkrit's vocabulary rather than pydantic-ai's.

A multi specialist question runs the orchestrator, then a nested agent per
specialist, then their tools. That is seconds of work behind one silent await,
and silence reads as a hang. ``AgentDeps.event_handler`` already threads a
pydantic-ai ``event_stream_handler`` into every run, orchestrator and nested
specialists alike, so the events exist. What was missing is meaning: the raw
stream speaks in ``FunctionToolCallEvent`` and tool names like ``ask_tax``,
which is framework detail no consumer should have to decode.

``progress_handler`` closes that gap. It consumes the raw stream and calls back
with ``Step`` values naming what is happening, which a caller renders however it
likes (a chat panel lighting one pill per specialist, a CLI printing a line, a
test collecting a list).

Two grains, because they mean different things to a reader:

  - SPECIALIST, an orchestrator delegation. ``ask_tax`` becomes the tax
    specialist starting, carrying the sub question it was handed. This is the
    grain a user cares about and the one the pills already display.
  - TOOL, a specialist's own domain call (``portfolio_volatility``). Finer,
    useful as a detail line, not something to build a UI around.

This module reports, it never decides. It holds no state between runs and
starts no work of its own.

Two things a consumer has to know, both consequences of a fan out running its
specialists concurrently:

  - FINISHED arrives in completion order, not call order. Two delegations
    issued risk then tax can finish tax then risk. Pair a finish to its start
    by ``call_id`` and never by position.
  - Every nested run shares this one handler, so TOOL steps from different
    specialists interleave with nothing saying which delegation each belongs
    to. SPECIALIST steps are unaffected, they carry their own call id.
    Attributing a tool step to its parent needs context the handler is not
    given.

Setting a handler at all puts pydantic-ai on its streaming request path, since
events only exist there. Leaving ``event_handler`` at None keeps the ordinary
non streaming request, which is the default everywhere.
"""
from __future__ import annotations

import inspect
from collections.abc import AsyncIterable, Awaitable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic_ai.messages import (
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    RetryPromptPart,
    ToolCallPart,
)

from finagent.conversation import SPECIALIST_TOOLS, sub_question


class StepKind(Enum):
    """Which grain of work a step describes.

    Explicit string values, never auto(): these are serialized to a UI and
    persisted in transcripts, so a reordered member must not renumber them.
    """

    SPECIALIST = "specialist"   # an orchestrator delegation (ask_risk, ask_tax, ...)
    TOOL = "tool"               # a specialist's own domain tool


class StepDetail(Enum):
    """How much of a step's payload to carry.

    A ladder, each level adding to the one before. The switch exists so the
    heavier fields can be refused at the source rather than filtered by the
    consumer: a payload never put on a Step cannot reach a log, a stored
    transcript, or a browser by mistake.

    SUMMARY is the default, so carrying answers and parameters is always a
    decision someone made rather than something that arrived by default.
    """

    # What happened and to whom: kind, status, name, call id, and the sub
    # question a delegation was handed. Enough to light a pill and label it.
    SUMMARY = "summary"
    # Adds the arguments a tool was called with and the answer a specialist
    # returned, so a reader can see the substance while it is still arriving
    # instead of waiting for the combined reply.
    FULL = "full"


class StepStatus(Enum):
    """Where in its lifecycle the step is. Same reason for explicit values."""

    STARTED = "started"
    FINISHED = "finished"
    # The tool raised and the model was handed the reason to try again (see the
    # ModelRetry translation in adapter/compiler.py). Reported rather than
    # hidden, since a retry is most of the wait a user is sitting through.
    RETRY = "retry"


@dataclass(frozen=True, slots=True)
class Step:
    """One thing that happened, at the moment it happened."""

    kind: StepKind
    status: StepStatus
    name: str          # "tax" for a specialist, "portfolio_volatility" for a tool
    detail: str = ""   # the sub question on a specialist start, else empty
    # Matches a FINISHED (or RETRY) back to its STARTED. A fan out issues
    # several calls before any returns, so position is not reliable.
    call_id: str = ""

    # StepDetail.FULL only, empty at SUMMARY.
    #
    # On a STARTED tool step, the parameters it was called with, so a reader
    # sees "volatility over 2024-01 to 2025-01" rather than "volatility".
    # Frozen does not deep freeze, this mapping is not copied on read, so a
    # consumer that mutates it corrupts every other consumer's view.
    args: Mapping[str, Any] = field(default_factory=dict)
    # On a FINISHED step, what came back: a specialist's answer verbatim, or a
    # tool's result. The same text conversation.py reports after the run, only
    # available while the user is still waiting for it.
    content: str = ""


def _tool_args(part: ToolCallPart) -> Mapping[str, Any]:
    # args_as_dict raises on malformed JSON from the model, which must not take
    # down progress for a run that is otherwise fine. Same forgiveness
    # sub_question applies to the delegation case.
    try:
        return part.args_as_dict()
    except Exception:  # noqa: BLE001
        return {}


def _started(event: FunctionToolCallEvent, detail: StepDetail) -> Step:
    part = event.part
    specialist = SPECIALIST_TOOLS.get(part.tool_name)
    if specialist is not None:
        # A delegation's only argument is the sub question, already carried in
        # `detail` at every level, so there is nothing left for `args` to add.
        return Step(
            kind=StepKind.SPECIALIST,
            status=StepStatus.STARTED,
            name=specialist,
            detail=sub_question(part),
            call_id=part.tool_call_id,
        )
    return Step(
        kind=StepKind.TOOL,
        status=StepStatus.STARTED,
        name=part.tool_name,
        call_id=part.tool_call_id,
        args=_tool_args(part) if detail is StepDetail.FULL else {},
    )


def _finished(event: FunctionToolResultEvent, detail: StepDetail) -> Step | None:
    part = event.part
    # RetryPromptPart carries an optional tool_name, and a retry that names no
    # tool cannot be attributed to anything a reader would recognize.
    tool_name = part.tool_name
    if tool_name is None:
        return None
    specialist = SPECIALIST_TOOLS.get(tool_name)
    status = StepStatus.RETRY if isinstance(part, RetryPromptPart) else StepStatus.FINISHED
    return Step(
        kind=StepKind.SPECIALIST if specialist is not None else StepKind.TOOL,
        status=status,
        name=specialist if specialist is not None else tool_name,
        call_id=part.tool_call_id,
        content=str(part.content) if detail is StepDetail.FULL else "",
    )


def to_step(event: AgentStreamEvent, detail: StepDetail = StepDetail.SUMMARY) -> Step | None:
    """The Step an event describes, or None for events that are not work
    boundaries (token deltas, part starts, the final result marker)."""
    if isinstance(event, FunctionToolCallEvent):
        return _started(event, detail)
    if isinstance(event, FunctionToolResultEvent):
        return _finished(event, detail)
    return None


def progress_handler(
    on_step: Callable[[Step], Any | Awaitable[Any]],
    detail: StepDetail = StepDetail.SUMMARY,
) -> Callable[[Any, AsyncIterable[AgentStreamEvent]], Awaitable[None]]:
    """
    An ``event_stream_handler`` for ``AgentDeps.event_handler`` that reports
    each work boundary to ``on_step``.

        steps: list[Step] = []
        assistant = Assistant(model=..., event_handler=progress_handler(steps.append))

    ``detail`` decides how much each step carries, SUMMARY by default. Pass
    ``StepDetail.FULL`` to include tool arguments and specialist answers, which
    is a decision worth making explicitly since those are the parts a reader
    would not want written somewhere unexpected.

    ``on_step`` may be sync or async, so an ``asyncio.Queue.put_nowait``, a
    ``list.append``, and an ``await websocket.send`` all work unchanged.

    A raising ``on_step`` is swallowed. Progress is a courtesy to the reader and
    must never be the reason an answer fails to arrive, so a broken consumer
    costs its own output and nothing else.
    """

    async def handler(_ctx: Any, events: AsyncIterable[AgentStreamEvent]) -> None:
        async for event in events:
            step = to_step(event, detail)
            if step is None:
                continue
            try:
                result = on_step(step)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001 - see docstring, progress never fails a run
                pass

    return handler
