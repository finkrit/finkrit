# finagent/tests/test_cli_flags.py
"""
The CLI's flags.

Mostly here for --ai, which is a released name kept alive by a second,
suppressed argument sharing --model's destination. Two argparse arguments
writing one dest is the kind of thing that reads correct and silently stops
working, and nobody notices until someone's script breaks.
"""
from __future__ import annotations

import argparse

from finagent.agent.base import DEFAULT_LANGUAGE
from finagent.cli import build_parser


def _parse(*argv: str) -> argparse.Namespace:
    return build_parser().parse_args(list(argv))


class TestModelFlag:

    def test_model_is_the_name(self):
        assert _parse("--model", "openai:gpt-5").model == "openai:gpt-5"

    def test_ai_still_reaches_the_same_place(self):
        assert _parse("--ai", "openai:gpt-5").model == "openai:gpt-5"

    def test_the_later_flag_wins_when_both_are_given(self):
        assert _parse("--ai", "old", "--model", "new").model == "new"
        assert _parse("--model", "new", "--ai", "old").model == "old"

    def test_neither_leaves_it_unset(self):
        # main falls through to FINKRIT_MODEL, so None has to survive.
        assert _parse().model is None

    def test_ai_is_not_advertised(self):
        # One name to learn. The alias works, it just is not taught.
        help_text = build_parser().format_help()
        assert "--model" in help_text
        assert "--ai" not in help_text

    def test_an_ollama_tag_is_not_mistaken_for_a_provider(self):
        # The colon in qwen2.5:14b is part of the name, and argparse must not
        # be the layer that has an opinion about it.
        assert _parse("--model", "qwen2.5:14b-instruct").model == "qwen2.5:14b-instruct"


class TestTraceFlags:

    def test_steps_and_truncation_are_independent(self):
        # --truncate-steps governs width, --steps governs what is carried, and
        # either without the other is a legitimate combination.
        args = _parse("--steps")
        assert args.steps and not args.truncate_steps
        args = _parse("--truncate-steps")
        assert args.truncate_steps and not args.steps

    def test_the_trace_is_on_and_untruncated_by_default(self):
        args = _parse()
        assert not args.quiet
        assert not args.truncate_steps
        assert not args.steps


class TestLanguageFlag:

    def test_it_defaults_to_the_shared_constant(self):
        # Not a literal "English" here, so the CLI and the agents cannot drift.
        assert _parse().lang == DEFAULT_LANGUAGE

    def test_a_plain_name_is_taken_as_given(self):
        assert _parse("--lang", "Thai").lang == "Thai"
