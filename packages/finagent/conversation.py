# finagent/conversation.py
"""
A threaded, multi-turn exchange with one agent.

`ask` on an agent is a single turn with no memory, ask it "what is my
volatility" and then "and my Sharpe" and the second question arrives with no
idea what "and" refers to. A Conversation carries the message history forward,
so follow-ups, pronouns, and refinements work.

History is the pydantic-ai message list, and it accumulates: every turn is
re-sent to the model, so a long exchange costs more tokens each turn. `max_turns`
caps it by dropping the oldest turns.

Trimming is done on whole user turns rather than on raw messages, because a turn
is not one message. A single question can produce several request and response
rounds while the model calls tools, and a ToolCallPart in one message is answered
by a ToolReturnPart in the next. Cutting between them would hand the model a
tool result it never asked for, so the cut is only ever made at the start of a
user turn.

Only the top-level agent's history is kept. When the runner is the orchestrator,
a specialist's internal tool loop happens inside a single tool call and never
reaches this history, which is what we want, the thread should read like the
conversation the user actually had.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Protocol

from pydantic_ai.messages import (
    ModelMessage,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from finagent.deps import AgentDeps

# The orchestrator delegates through one tool per specialist. Reading these back
# off the run is how we know which domains actually answered, which the UI shows
# so a user can see the fan out rather than take the answer on faith.
SPECIALIST_TOOLS = {
    "ask_risk": "risk",
    "ask_performance": "performance",
    "ask_optimization": "optimization",
    "ask_tax": "tax",
}

# Enough turns for a real working session, bounded so a long-lived tab does not
# grow the prompt without limit. Not tuned against real usage yet.
DEFAULT_MAX_TURNS = 40


class _Runner(Protocol):
    """What a Conversation needs from an agent: a run that accepts prior
    messages and returns a result carrying the updated history. Both
    CapabilityAgent and Orchestrator satisfy this."""

    def run(self, question: str, deps: AgentDeps, message_history: list[ModelMessage] | None) -> Any: ...

    async def run_async(self, question: str, deps: AgentDeps, message_history: list[ModelMessage] | None) -> Any: ...


def _turn_starts(messages: list[ModelMessage]) -> list[int]:
    # A user turn begins at the message carrying the user's prompt. Everything
    # after it, up to the next one, belongs to that turn (tool calls, tool
    # returns, and the final answer).
    return [
        index
        for index, message in enumerate(messages)
        if any(isinstance(part, UserPromptPart) for part in getattr(message, "parts", []))
    ]


@dataclass(frozen=True, slots=True)
class SpecialistAnswer:
    """One specialist's own reply, before the orchestrator folded it into the
    combined answer."""

    name: str        # risk, performance, optimization, tax
    question: str    # the sub-question the orchestrator handed it
    answer: str      # what it returned, verbatim


def _specialists_called(messages: list[ModelMessage]) -> list[SpecialistAnswer]:
    """Each specialist the orchestrator delegated to, with the sub-question it
    was given and the answer it gave, in call order.

    Read off the run rather than off the final text. The orchestrator is told
    never to alter a specialist's numbers, but "told not to" is not a guarantee,
    and the point of showing the work is to let a user check the combined answer
    against what the specialist actually said. Only the transcript can do that.

    A call is matched to its return by tool_call_id, since a fan out issues
    several calls before any of them come back and position is not reliable. A
    call whose return never arrived (the run stopped early, the tool raised) is
    dropped, because a specialist with no answer has nothing to show.
    """
    asked: dict[str, tuple[str, str]] = {}   # call id -> (specialist, sub-question)
    order: list[str] = []                    # call ids, in the order issued
    returned: dict[str, str] = {}            # call id -> answer

    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                name = SPECIALIST_TOOLS.get(part.tool_name)
                if name is None:
                    continue
                asked[part.tool_call_id] = (name, sub_question(part))
                order.append(part.tool_call_id)
            elif isinstance(part, ToolReturnPart) and part.tool_call_id in asked:
                returned[part.tool_call_id] = str(part.content)

    return [
        SpecialistAnswer(name=asked[call_id][0], question=asked[call_id][1],
                         answer=returned[call_id])
        for call_id in order
        if call_id in returned
    ]


def answer_of(result: Any) -> str:
    """The answer a user should see, which is not always the model's last text.

    When exactly one specialist answered, there is nothing to combine. The
    orchestrator's closing text is then a second generation restating content it
    was told not to alter, which is all risk and no benefit: it is the longest
    prose in the run, produced last, over numbers it must copy exactly.

    Both observed failures took that shape. A specialist answered correctly in
    English and the orchestrator restated one beta as -0.05 where the specialist
    said -0.06. And a specialist answered correctly in Chinese, whereupon the
    orchestrator, instructed in English but summarizing Chinese content,
    followed the content and replied in Thai. Neither rewrite added anything a
    reader wanted, and passing the specialist's answer through verbatim makes
    both impossible rather than unlikely.

    A fan out across several specialists still needs combining, so it falls
    through. So does a plain CapabilityAgent run, which delegates to nobody and
    finds no specialist calls at all.

    ``new_messages()``, never ``all_messages()``. In a threaded conversation the
    latter carries every prior turn, so turn two finds turn one's specialist
    call, counts exactly one, and returns turn one's answer. Every follow up
    then repeats the first reply verbatim.
    """
    answers = _specialists_called(result.new_messages())
    if len(answers) == 1 and answers[0].answer.strip():
        return answers[0].answer
    return result.output


def sub_question(part: ToolCallPart) -> str:
    # Every ask_* tool takes a single question argument. args_as_dict raises on
    # malformed JSON from the model, which must not take down a reply that
    # otherwise succeeded, so a bad payload just yields no sub-question.
    # Public because finagent.progress reads the same sub-question live, off
    # the event stream, and the two must agree on how it is extracted.
    try:
        args = part.args_as_dict()
    except Exception:
        return ""
    return str(args.get("question", ""))


def trim_to_turns(messages: list[ModelMessage], max_turns: int) -> list[ModelMessage]:
    """Keep the most recent `max_turns` user turns, cutting only at a turn
    boundary so no tool call is separated from its result."""
    if max_turns <= 0:
        return []
    starts = _turn_starts(messages)
    if len(starts) <= max_turns:
        return messages
    return messages[starts[len(starts) - max_turns]:]


class Conversation:
    """
    A stateful thread over one agent.

        chat = assistant.conversation()            # the orchestrator
        chat.ask("what is my volatility?")
        chat.ask("and how does that compare to my drawdown?")   # remembers

    Not thread-safe: one Conversation is one exchange with one user. A server
    keeps one per session rather than sharing one across requests.
    """

    def __init__(
        self,
        runner: _Runner,
        deps: AgentDeps | Callable[[], AgentDeps],
        max_turns: int = DEFAULT_MAX_TURNS,
    ) -> None:
        # deps may be a callable, Assistant.deps is a property rebuilt per call
        # so a conversation always sees the current store and registry.
        self._runner = runner
        self._deps = deps
        self._max_turns = max_turns
        self._messages: list[ModelMessage] = []
        self._last_specialists: list[SpecialistAnswer] = []

    @property
    def _current_deps(self) -> AgentDeps:
        return self._deps() if callable(self._deps) else self._deps

    @property
    def messages(self) -> list[ModelMessage]:
        """The thread so far. A copy, so a caller cannot mutate our state."""
        return list(self._messages)

    @property
    def turns(self) -> int:
        """How many user questions this conversation holds."""
        return len(_turn_starts(self._messages))

    def reset(self) -> None:
        """Start over. The next question arrives with no prior context."""
        self._messages = []

    def ask(self, question: str, event_handler: Callable | None = None) -> str:
        result = self._runner.run(
            question, self._deps_for(event_handler), self._messages or None
        )
        self._absorb(result)
        return answer_of(result)

    async def ask_async(self, question: str, event_handler: Callable | None = None) -> str:
        result = await self._runner.run_async(
            question, self._deps_for(event_handler), self._messages or None
        )
        self._absorb(result)
        return answer_of(result)

    def _deps_for(self, event_handler: Callable | None) -> AgentDeps:
        """Deps for one turn, with a per-turn progress handler if given.

        The handler cannot simply live on the Assistant: a server holds one
        Assistant for every request, so a handler set there would deliver one
        user's steps into another user's stream. Overriding per turn scopes it
        to the caller that asked for it. None keeps whatever the deps already
        carry, which is how a single user process sets one globally."""
        deps = self._current_deps
        if event_handler is None:
            return deps
        return replace(deps, event_handler=event_handler)

    @property
    def last_specialists(self) -> list[SpecialistAnswer]:
        """What each specialist said on the most recent question, in the order
        the orchestrator called them. Empty when a specialist was threaded
        directly, since there is no fan out to report in that case."""
        return list(self._last_specialists)

    @property
    def last_specialist_names(self) -> list[str]:
        """Just the names, deduped. The pills above a reply, where the same
        specialist called twice should still read as one."""
        seen: list[str] = []
        for answer in self._last_specialists:
            if answer.name not in seen:
                seen.append(answer.name)
        return seen

    def _absorb(self, result: Any) -> None:
        # all_messages() is the prior history plus this turn, which is exactly
        # what the next turn should be primed with.
        self._messages = trim_to_turns(result.all_messages(), self._max_turns)
        self._last_specialists = _specialists_called(result.new_messages())
