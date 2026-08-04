# tests/test_readme.py
"""
Holds the README to what the code actually does.

The README is the PyPI description. It is the whole of what a user sees on the
project page, because PyPI has no release notes field and never diffs one
version against another, so a stale README is not a documentation problem, it
is the shipped product being wrong.

It went stale exactly the way these things do. A tax specialist was added as
agent 4, the CLI help was updated, and the README kept saying "three specialists
and a router" and offering `-ag 0|1|2|3`. Nothing failed. The same happened to
the CSV column table when a real brokerage export forced new aliases in.

So the checks here are all of one shape: read the truth out of the code, then
assert the README says it. They are deliberately narrow, covering the tables and
enumerations that go stale silently, not prose. Prose that drifts is a review
problem. A published list of accepted column names that omits half of them makes
a user think their file will not load.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from finagent.cli import _AGENT_CHOICES, _AGENT_NAMES

# Moved out of finagent.cli: the terminal loader and the upload path share one
# alias table now, so the README documents a single contract rather than the
# CLI's half of one.
from finagent.ingest import CSV_ALIASES, CSV_DATE_FORMATS

REPO_ROOT = Path(__file__).resolve().parent.parent
README = (REPO_ROOT / "README.md").read_text()

# Spelled out counts, since the README says "four specialists" rather than "4".
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

SPECIALISTS = {key: choice for key, choice in _AGENT_CHOICES.items() if choice[0] is not None}


@pytest.mark.parametrize("key,label", [(k, v[1]) for k, v in _AGENT_CHOICES.items()])
def test_every_agent_appears_in_the_readme(key: str, label: str):
    # The agent table. A specialist nobody can find is a specialist nobody uses.
    name = label.split(" (")[0]
    assert re.search(rf"\b{re.escape(name)}\b", README, re.IGNORECASE), (
        f"agent {key} ({name}) is in _AGENT_CHOICES but never named in the README. "
        f"It ships in the CLI menu and on the PyPI page nobody knows it exists."
    )


@pytest.mark.parametrize("key", sorted(SPECIALISTS))
def test_every_specialist_number_is_documented(key: str):
    # The README explains the numbering in prose ("`0` router, `1` risk, ...").
    # Adding agent 4 without touching that sentence is the drift that happened.
    numbering = re.search(r"Numbers are ([^.]+)\.", README)
    assert numbering, "the README no longer explains the -ag numbering, update this test with it"
    assert f"`{key}`" in numbering.group(1), (
        f"agent {key} ({SPECIALISTS[key][1]}) is missing from the README's numbering: "
        f"{numbering.group(1).strip()}"
    )


def test_the_agent_flag_range_covers_every_agent():
    # The `-ag 0|1|2|3` line in the flag list. Stale ranges read as a hard
    # limit. Only pipe-separated ranges are checked: a bare `-ag 1` in a usage
    # example picks one agent and is supposed to name just one.
    ranges = re.findall(r"-ag\s+(\d(?:\|\d)+)", README)
    assert ranges, "no -ag range documented in the README"
    expected = set(_AGENT_CHOICES)
    for found in ranges:
        assert set(found.split("|")) == expected, (
            f"the README offers `-ag {found}` but the CLI accepts "
            f"{'|'.join(sorted(expected))}"
        )


def test_the_specialist_count_is_right():
    # "three specialists and a router" outlived the third specialist.
    match = re.search(r"(\w+) specialists", README)
    assert match, "the README no longer counts the specialists, update this test with it"
    word = match.group(1).lower()
    assert word in NUMBER_WORDS, f"unexpected count word {word!r} in the README"
    assert NUMBER_WORDS[word] == len(SPECIALISTS), (
        f"the README says {word} specialists, there are {len(SPECIALISTS)}: "
        f"{', '.join(sorted(v[1] for v in SPECIALISTS.values()))}"
    )


@pytest.mark.parametrize(
    "field,alias",
    [(field, alias) for field, aliases in CSV_ALIASES.items() for alias in aliases],
)
def test_every_csv_alias_is_documented(field: str, alias: str):
    # The recognized column names table. Someone reads this to decide whether
    # their export needs renaming, so an omission costs a user real work.
    assert f"`{alias}`" in README, (
        f"the CSV loader accepts {alias!r} for {field} but the README's column "
        f"table does not list it, so nobody knows their export already works"
    )


@pytest.mark.parametrize("fmt", [f for f in CSV_DATE_FORMATS if f != "iso"])
def test_every_date_format_is_documented(fmt: str):
    # strptime patterns as a reader sees them: %m/%d/%Y is MM/DD/YYYY.
    human = fmt.replace("%m", "MM").replace("%d", "DD").replace("%Y", "YYYY").replace("%y", "YY")
    assert f"`{human}`" in README, (
        f"the CSV loader parses {human} dates, the README does not say so"
    )


def test_iso_dates_are_documented():
    assert "`YYYY-MM-DD`" in README


@pytest.mark.parametrize("name", sorted(set(_AGENT_NAMES) - {"all"}))
def test_agent_name_aliases_resolve_to_a_real_agent(name: str):
    # Not a README check. The alias table is hand maintained next to the agent
    # table, and an alias pointing at a number that no longer exists fails only
    # when a user types it.
    assert _AGENT_NAMES[name] in _AGENT_CHOICES, (
        f"-ag {name} maps to agent {_AGENT_NAMES[name]}, which does not exist"
    )
