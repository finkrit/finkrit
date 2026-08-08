# finagent/provenance.py
"""
Every figure in an answer has to trace back to something a tool returned.

The premise of this stack is that computed values reach the reader exactly as
the engine produced them. Everything protecting that premise so far has been an
instruction: never invent a number, report only what a specialist returned,
never add a company name from your own knowledge. Instructions are complied
with most of the time, which is a different thing from being true, and each
observed breach was silent. A reader cannot tell a copied number from an
invented one by looking at it.

This reads the answer back and checks it. Each number in the prose must be a
faithful rendering of some number the run actually received, where faithful
allows the transformations a writer legitimately makes:

    0.250626  ->  0.2506, 0.25, 25.06%    rounding, and fraction to percent
    -0.138    ->  -13.80%                 sign and scale preserved
    1471.5    ->  $1,471.50               separators and currency decoration

and rejects the one it must not make: a digit that changes. A beta of
-0.0578348 may be written -0.06 or -0.058. It may not be written -0.05, which
is the failure that prompted this, seen when an orchestrator restated a
specialist's number.

What counts as a source is deliberately wide. Numbers are harvested from every
tool result in the run, out of nested dicts and lists and out of the strings
inside them, so the "95%" in a units line and the dates in a window both count.
Wide because a false alarm costs a retry on a correct answer, and the check
earns its place only if that is rare.

Two boundaries worth stating, because this catches less than its name suggests.

It does not check that a number answers the question asked. A model that
reports beta when volatility was wanted passes here, since beta was genuinely
computed. That is the staleness problem and it is still open.

It does not check prose. "NVIDIA is riskiest because the semiconductor sector
is prone to product cycle swings" contains no figure and passes untouched. Only
numbers are verifiable this cheaply, and an invented causal story remains
invented.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import ModelMessage, ToolReturnPart

# A bare integer below this is read as a count, an ordinal, or part of a name
# rather than as a measurement: "12 holdings", "the top 3", "S&P 500", "one
# period". None of those are numbers the engine produced, and demanding a
# source for them would flag correct answers constantly. Measured quantities in
# this domain essentially always carry a decimal or a percent sign, and those
# are never skipped whatever their size, so the exemption costs little. Above
# the ceiling an integer is large enough to be a currency amount, which is
# exactly the shape of the observed "$1,014" fabrication, so it is checked.
COUNT_CEILING = 1000

# Enough of the offending figures to act on without pasting the whole answer
# back at the model.
FIGURES_IN_MESSAGE = 8

# Sign is only a sign when nothing runs into it from the left, so the "-08" in
# "2026-08-08" reads as 8 rather than as minus eight. Thousands separators are
# taken in and stripped, since "$1,471.50" is one number. A trailing percent is
# captured because it decides whether a bare integer is a measurement: "25%" is
# a claim about volatility where "25" beside "holdings" is not.
_NUMBER = re.compile(r"(?<![\w.,])(-?\d[\d,]*(?:\.\d+)?)(%?)")

# Floats that came out of a division do not land exactly on the boundary they
# ought to, so the half unit tolerance below is opened by a hair. Small enough
# to change no verdict that was not already on the line.
_SLACK = 1 + 1e-9


@dataclass(frozen=True, slots=True)
class Figure:
    """One number as the answer wrote it, kept alongside how it was written.

    ``decimals`` is the whole point of carrying the text: it says how precisely
    the writer committed, and therefore how far from a source value the figure
    is allowed to sit. Written to two places, a figure claims its source rounds
    to those two places and nothing more.
    """

    text: str        # as it appeared, for an error message a human will read
    value: float
    decimals: int
    percent: bool

    @property
    def checkable(self) -> bool:
        return self.percent or self.decimals > 0 or abs(self.value) >= COUNT_CEILING


def figures_in(text: str) -> list[Figure]:
    """Every number written in ``text``, in the order it appears."""
    found: list[Figure] = []
    for digits, percent in _NUMBER.findall(text):
        plain = digits.replace(",", "")
        try:
            value = float(plain)
        except ValueError:  # pragma: no cover - the pattern cannot produce one
            continue
        _, _, fraction = plain.partition(".")
        found.append(
            Figure(
                text=digits + percent,
                value=value,
                decimals=len(fraction),
                percent=bool(percent),
            )
        )
    return found


def numbers_in(value: Any) -> set[float]:
    """Every number reachable inside a tool result.

    Walks dicts, lists, and tuples, and reads the strings it finds on the way,
    because a payload carries figures in its prose as well as in its floats:
    the confidence level sits inside a units line, the lookback inside a window
    description. A number the run was told is a number the answer may state.

    Booleans are excluded. ``True`` is an ``int`` in Python and would otherwise
    quietly license the figure 1.
    """
    found: set[float] = set()
    _harvest(value, found)
    return found


def _harvest(value: Any, into: set[float]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isfinite(number):
            into.add(number)
    elif isinstance(value, str):
        for figure in figures_in(value):
            into.add(figure.value)
    elif isinstance(value, dict):
        for key, item in value.items():
            _harvest(key, into)
            _harvest(item, into)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _harvest(item, into)


def sources_from_messages(messages: Iterable[ModelMessage]) -> set[float]:
    """Every number this run received back from a tool.

    Includes earlier turns of a threaded conversation, and that is intended. A
    number the engine computed on turn one is not a fabrication when it is
    quoted again on turn three. Whether it is still the right number to quote
    is a separate question this does not answer.

    For a specialist the returns are payload dicts. For the orchestrator they
    are the specialists' own prose, whose figures are harvested from the text,
    which is what makes an altered restatement visible.
    """
    found: set[float] = set()
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart):
                _harvest(part.content, found)
    return found


def _renders(source: float, figure: Figure) -> bool:
    # A figure written to d decimals is a faithful rendering of source when
    # source rounds to it, which is to say they sit within half a unit in the
    # figure's last place. Truncation is not rounding and fails here on
    # purpose: -0.0578 written as -0.05 is the error this exists to catch.
    if not math.isfinite(source):
        return False
    tolerance = 0.5 * (10.0 ** -figure.decimals) * _SLACK
    return abs(source - figure.value) <= tolerance


def is_supported(figure: Figure, sources: Iterable[float]) -> bool:
    """Whether some source number renders as ``figure``.

    A fraction may be written as a percentage and a percentage as a fraction,
    so each source is tried at its own scale and at both hundredfold shifts.
    That is generous by design: it lets 0.0205 justify "2.05%" without the
    checker having to know which metrics are fractions, and the cost is that a
    genuine number and its own hundredfold are not distinguished. Units belong
    in the payload, which is where they now are, not in this test.
    """
    for source in sources:
        if _renders(source, figure) or _renders(source * 100.0, figure):
            return True
        if _renders(source / 100.0, figure):
            return True
    return False


def unsupported(answer: str, sources: Iterable[float]) -> list[str]:
    """The figures in ``answer`` that no source accounts for, deduplicated and
    in the order they were written."""
    known = list(sources)
    seen: set[str] = set()
    bad: list[str] = []
    for figure in figures_in(answer):
        if not figure.checkable or figure.text in seen:
            continue
        if not is_supported(figure, known):
            seen.add(figure.text)
            bad.append(figure.text)
    return bad


def _listed(figures: list[str]) -> str:
    shown = ", ".join(figures[:FIGURES_IN_MESSAGE])
    if len(figures) > FIGURES_IN_MESSAGE:
        shown += f", and {len(figures) - FIGURES_IN_MESSAGE} more"
    return shown


def retry_message(figures: list[str]) -> str:
    # Says what to do, not only what is wrong. A model told merely that a
    # number is unsupported has an easy way out, which is to write a different
    # unsupported number, so the instruction names the two acceptable repairs
    # and rules out the third.
    return (
        f"These figures do not appear in any tool result: {_listed(figures)}. "
        "Every number in your answer must come from a result you were given, "
        "either exactly or as a correct rounding or percentage of it. Reread "
        "the results, replace each figure with the value actually returned, or "
        "drop the claim if no result supports it. Do not calculate a new "
        "number and do not supply one from memory."
    )


def warning_for(figures: list[str]) -> str:
    # The end of the line, when retries are spent and the model will not
    # correct itself. Returning the answer with the doubt attached beats both
    # alternatives: failing the run leaves the user with nothing over a figure
    # that may be a formatting quirk, and passing it silently is the very thing
    # this module exists to prevent.
    return (
        f"\n\n[unverified: {_listed(figures)} could not be traced to a "
        f"computed result and may not be reliable]"
    )


def install_provenance(agent: Agent) -> None:
    """Register the check as ``agent``'s output validator.

    An output validator rather than a wrapper around the answer, because
    pydantic-ai gives a validator the one thing a wrapper cannot have: a
    ModelRetry that puts the complaint back in front of the model with the tool
    results still in context. A wrapper could only report the problem after the
    run had ended.

    Retries are the agent's own allowance. Once it is spent the answer is
    returned annotated rather than raised on, so a stubborn model costs the
    reader a caveat instead of the whole reply.
    """

    @agent.output_validator
    def _provenance(ctx: RunContext[Any], answer: Any) -> Any:
        # Structured outputs are validated by their own schema and carry no
        # prose for a figure to hide in.
        if not isinstance(answer, str):
            return answer
        bad = unsupported(answer, sources_from_messages(ctx.messages))
        if not bad:
            return answer
        # No tool result at all is the worst case rather than an exemption: a
        # numeric answer to a numeric question with nothing computed behind it
        # is entirely invented. It falls out of the same test, since an empty
        # source set supports nothing.
        if _retries_left(ctx):
            raise ModelRetry(retry_message(bad))
        return answer + warning_for(bad)


def _retries_left(ctx: RunContext[Any]) -> bool:
    # Read defensively. These are pydantic-ai's own counters and a version that
    # renames or drops one should cost a retry, not raise inside a validator
    # and take down an answer that was otherwise ready.
    used = getattr(ctx, "retry", 0) or 0
    allowed = getattr(ctx, "max_retries", 0) or 0
    return used < allowed
