# finagent/tests/test_cli_steps.py
"""
The CLI's live step trace.

What matters is the line a reader sees, so these assert the rendered string
rather than the Step that produced it.
"""
from __future__ import annotations

from finagent.cli import _render
from finagent.progress import Step, StepDetail, StepKind, StepStatus


def _specialist(status, name="tax", detail="", content=""):
    return Step(kind=StepKind.SPECIALIST, status=status, name=name,
                detail=detail, content=content, call_id="c1")


def _tool(status, name="portfolio_volatility", args=None):
    return Step(kind=StepKind.TOOL, status=status, name=name,
                args=args or {}, call_id="c2")


class TestSpecialistLines:

    def test_start_names_the_specialist_and_its_sub_question(self):
        step = _specialist(StepStatus.STARTED, detail="what is harvestable before year end")
        assert _render(step) == "  → asking tax: what is harvestable before year end"

    def test_start_without_a_sub_question_is_still_readable(self):
        assert _render(_specialist(StepStatus.STARTED)) == "  → asking tax"

    def test_finish_is_shown_because_the_wait_is_between_the_two(self):
        assert _render(_specialist(StepStatus.FINISHED)) == "  ✓ tax answered"

    def test_finish_carries_the_answer_at_full_detail(self):
        step = _specialist(StepStatus.FINISHED, content="Harvestable losses total $4,180.")
        assert _render(step) == "  ✓ tax answered  Harvestable losses total $4,180."

    def test_retry_is_surfaced_rather_than_hidden(self):
        # A retry is most of the wait when it happens, so silence would be the
        # worst thing to show.
        assert _render(_specialist(StepStatus.RETRY)) == "  ⟳ tax retrying"


class TestToolLines:

    def test_tool_start_is_indented_under_its_specialist(self):
        assert _render(_tool(StepStatus.STARTED)) == "      · portfolio_volatility"

    def test_tool_finish_is_not_shown(self):
        # Showing both doubles the trace to say nothing new: the answer that
        # follows is the evidence the tool returned.
        assert _render(_tool(StepStatus.FINISHED)) is None

    def test_arguments_appear_at_full_detail(self):
        step = _tool(StepStatus.STARTED, name="asset_beta", args={"ticker": "AAPL"})
        assert _render(step) == "      · asset_beta  ticker=AAPL"

    def test_portfolio_id_is_dropped_from_arguments(self):
        # An opaque handle every tool takes. It says nothing to a reader and
        # would push the useful arguments off the line.
        step = _tool(StepStatus.STARTED, args={"portfolio_id": "primary", "interval": "1d"})
        assert _render(step) == "      · portfolio_volatility  interval=1d"


class TestClipping:

    def test_a_long_answer_is_cut_to_one_line(self):
        step = _specialist(StepStatus.FINISHED, content="x" * 400)
        line = _render(step)
        assert line.endswith("…")
        assert len(line) < 100

    def test_newlines_are_flattened(self):
        # A multi-line answer must not break the spinner's single line redraw.
        step = _specialist(StepStatus.FINISHED, content="first line\n\nsecond line")
        assert _render(step) == "  ✓ tax answered  first line second line"


class TestDetailGating:
    """The renderer shows whatever the Step carries, and SUMMARY carries
    neither args nor content, so the flag is what actually gates the output."""

    def test_summary_steps_render_without_args_or_answers(self):
        assert _render(_tool(StepStatus.STARTED)) == "      · portfolio_volatility"
        assert _render(_specialist(StepStatus.FINISHED)) == "  ✓ tax answered"

    def test_the_two_levels_are_distinct(self):
        assert StepDetail.SUMMARY is not StepDetail.FULL
