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

from typing import Any, Callable, Protocol

from pydantic_ai.messages import ModelMessage, ToolCallPart, UserPromptPart

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
DEFAULT_MAX_TURNS = 20


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


def _specialists_called(messages: list[ModelMessage]) -> list[str]:
    """Names of the specialists the orchestrator delegated to in these messages,
    in call order and without repeats."""
    called: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                name = SPECIALIST_TOOLS.get(part.tool_name)
                if name is not None and name not in called:
                    called.append(name)
    return called


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
        self._last_specialists: list[str] = []

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

    def ask(self, question: str) -> str:
        result = self._runner.run(question, self._current_deps, self._messages or None)
        self._absorb(result)
        return result.output

    async def ask_async(self, question: str) -> str:
        result = await self._runner.run_async(question, self._current_deps, self._messages or None)
        self._absorb(result)
        return result.output

    @property
    def last_specialists(self) -> list[str]:
        """Which specialists answered the most recent question, in the order the
        orchestrator called them. Empty when a specialist was threaded directly,
        since there is no fan out to report in that case."""
        return list(self._last_specialists)

    def _absorb(self, result: Any) -> None:
        # all_messages() is the prior history plus this turn, which is exactly
        # what the next turn should be primed with.
        self._messages = trim_to_turns(result.all_messages(), self._max_turns)
        self._last_specialists = _specialists_called(result.new_messages())
