# finagent/tests/test_provenance.py
"""
Provenance: every figure in an answer traces back to a tool result.

Most of these are drawn from real traces against a local qwen2.5 14b, since the
check is only worth having if it passes the answers that were right and fails
the ones that were wrong. Both sides are tested, and the passing side matters
more: a false alarm costs a retry on a correct answer.
"""
from __future__ import annotations

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.provenance import (
    figures_in,
    install_provenance,
    is_supported,
    numbers_in,
    sources_from_messages,
    unsupported,
)


def _texts(text: str) -> list[str]:
    return [figure.text for figure in figures_in(text)]


class TestReadingNumbersOutOfProse:

    def test_a_decimal_keeps_its_precision(self):
        figure = figures_in("beta is 0.7610")[0]
        assert (figure.value, figure.decimals) == (0.761, 4)

    def test_thousands_separators_are_one_number(self):
        figure = figures_in("a loss of $1,471.50")[0]
        assert (figure.value, figure.decimals) == (1471.5, 2)

    def test_a_percent_is_recorded_as_one(self):
        assert figures_in("volatility of 25.06%")[0].percent

    def test_a_leading_minus_is_a_sign(self):
        assert figures_in("beta of -0.058")[0].value == pytest.approx(-0.058)

    def test_a_date_is_not_three_negative_numbers(self):
        # "2026-08-08" must read as 2026, 8, 8. A hyphen between digits is a
        # separator, and reading it as a sign would invent numbers the answer
        # never claimed and then fail to source them.
        assert [f.value for f in figures_in("from 2025-08-08 to 2026-08-08")] == [
            2025.0, 8.0, 8.0, 2026.0, 8.0, 8.0,
        ]

    def test_prose_with_no_numbers_yields_none(self):
        assert _texts("NVIDIA is the most sensitive to market movements.") == []


class TestWhichFiguresAreWorthChecking:

    def test_a_count_is_not_a_measurement(self):
        # "12 holdings" is the model counting a list it was given, not quoting
        # a computed value, and nothing in a payload says 12.
        assert unsupported("You hold 12 positions.", []) == []

    def test_a_benchmark_name_is_not_a_measurement(self):
        assert unsupported("relative to the S&P 500 (^GSPC)", []) == []

    def test_a_small_integer_with_a_percent_sign_is_a_measurement(self):
        # The exemption is for bare integers only. "25%" is a claim about
        # volatility whatever else is true of it.
        assert unsupported("volatility of 25%", []) == ["25%"]

    def test_a_currency_sized_integer_is_a_measurement(self):
        # The shape of the observed fabrication: VaR, a fraction, reported as
        # "$1,014" for the portfolio.
        assert unsupported("value at risk of $1,014", []) == ["1,014"]


class TestFaithfulRenderings:

    def test_an_exact_quote_is_supported(self):
        assert is_supported(figures_in("0.250626")[0], [0.250626])

    def test_rounding_is_supported(self):
        assert is_supported(figures_in("0.2506")[0], [0.250626])
        assert is_supported(figures_in("0.25")[0], [0.250626])

    def test_a_fraction_may_be_written_as_a_percentage(self):
        assert is_supported(figures_in("25.06%")[0], [0.250626])
        assert is_supported(figures_in("2.05%")[0], [0.0204773])

    def test_a_negative_fraction_keeps_its_sign_and_scale(self):
        assert is_supported(figures_in("-13.80%")[0], [-0.138])

    def test_separators_and_currency_do_not_break_a_match(self):
        assert is_supported(figures_in("$1,471.50")[0], [1471.5])

    def test_a_changed_digit_is_not_supported(self):
        # The failure this exists for. A beta of -0.0578348 may be written
        # -0.06. It may not be written -0.05.
        source = -0.0578348
        assert is_supported(figures_in("-0.06")[0], [source])
        assert not is_supported(figures_in("-0.05")[0], [source])

    def test_truncation_is_not_rounding(self):
        assert not is_supported(figures_in("0.2505")[0], [0.250626])

    def test_nothing_computed_supports_nothing(self):
        assert not is_supported(figures_in("12.5%")[0], [])


class TestHarvestingSources:

    def test_numbers_come_out_of_nested_results(self):
        payload = {"holdings": {"AAPL": {"beta": 0.745365}}, "computed": ["beta"]}
        assert 0.745365 in numbers_in(payload)

    def test_numbers_inside_strings_count(self):
        # The confidence level lives in a units line and the lookback in a
        # window description, and an answer is entitled to quote both.
        payload = {"units": {"value_at_risk": "fraction lost, 95% confidence"}}
        assert 95.0 in numbers_in(payload)

    def test_a_boolean_is_not_the_number_one(self):
        assert numbers_in({"capped": True, "note": ""}) == set()

    def test_a_specialists_prose_is_a_source(self):
        # What the orchestrator is checked against. Its tool returns are the
        # specialists' answers, so their figures have to be readable as sources
        # or every combined answer would fail.
        messages: list[ModelMessage] = [
            ModelResponse(parts=[ToolCallPart(tool_name="ask_risk", args={"question": "beta"},
                                              tool_call_id="c1")]),
            ModelRequest(parts=[ToolReturnPart(tool_name="ask_risk", tool_call_id="c1",
                                               content="AAPL beta is 0.745365.")]),
        ]
        assert 0.745365 in sources_from_messages(messages)


class TestFlaggingAnAnswer:

    def test_a_faithful_answer_is_clean(self):
        payload = {"metrics": {"volatility": 0.250626, "beta": -0.0578348}}
        answer = "Volatility is 25.06% and beta is -0.06 over 365 calendar days."
        assert unsupported(answer, numbers_in(payload)) == []

    def test_an_altered_number_is_flagged(self):
        payload = {"metrics": {"beta": -0.0578348}}
        assert unsupported("beta is -0.05", numbers_in(payload)) == ["-0.05"]

    def test_a_currency_conversion_it_could_not_have_made_is_flagged(self):
        # VaR came back as the fraction 0.0204773 with no position values in
        # sight, and was reported as $204.77.
        payload = {"metrics": {"value_at_risk": 0.0204773}}
        assert unsupported("value at risk is $204.77", numbers_in(payload)) == ["204.77"]

    def test_the_same_bad_figure_is_reported_once(self):
        answer = "beta is -0.05, and again -0.05"
        assert unsupported(answer, [-0.0578348]) == ["-0.05"]

    def test_figures_are_reported_in_the_order_written(self):
        assert unsupported("first 9.91%, then 8.81%", []) == ["9.91%", "8.81%"]


def _agent(script) -> Agent:
    agent = Agent(FunctionModel(script), retries=2)

    @agent.tool_plain
    def portfolio_risk() -> dict:
        """The portfolio's risk metrics."""
        return {"volatility": 0.250626}

    install_provenance(agent)
    return agent


def _called_tool(messages: list[ModelMessage]) -> bool:
    return any(
        isinstance(part, ToolReturnPart)
        for message in messages
        for part in getattr(message, "parts", [])
    )


class TestTheValidatorInARun:

    def test_a_fabricated_figure_is_sent_back_and_corrected(self):
        said: list[str] = []

        def script(messages, info: AgentInfo) -> ModelResponse:
            if not _called_tool(messages):
                return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_risk", args={})])
            text = "Your volatility is 99.99%." if not said else "Your volatility is 25.06%."
            said.append(text)
            return ModelResponse(parts=[TextPart(text)])

        result = _agent(script).run_sync("how risky am I?")
        assert result.output == "Your volatility is 25.06%."
        assert len(said) == 2, "the first answer should have been sent back"

    def test_the_retry_names_the_offending_figure(self):
        seen: list[str] = []

        def script(messages, info: AgentInfo) -> ModelResponse:
            if not _called_tool(messages):
                return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_risk", args={})])
            if seen:
                # The complaint arrives as the latest user visible content.
                seen.append(str(messages[-1]))
                return ModelResponse(parts=[TextPart("Your volatility is 25.06%.")])
            seen.append("")
            return ModelResponse(parts=[TextPart("Your volatility is 99.99%.")])

        _agent(script).run_sync("how risky am I?")
        assert "99.99%" in seen[-1]

    def test_a_stubborn_model_gets_an_answer_with_the_doubt_attached(self):
        # Retries spent and still unsupported. Annotating beats raising: the
        # reader keeps an answer that is mostly right and can see which figure
        # is not, where a failed run leaves them with nothing.
        def script(messages, info: AgentInfo) -> ModelResponse:
            if not _called_tool(messages):
                return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_risk", args={})])
            return ModelResponse(parts=[TextPart("Your volatility is 99.99%.")])

        result = _agent(script).run_sync("how risky am I?")
        assert result.output.startswith("Your volatility is 99.99%.")
        assert "unverified" in result.output
        assert "99.99%" in result.output.split("unverified")[1]

    def test_a_faithful_answer_passes_first_time(self):
        turns: list[int] = []

        def script(messages, info: AgentInfo) -> ModelResponse:
            if not _called_tool(messages):
                return ModelResponse(parts=[ToolCallPart(tool_name="portfolio_risk", args={})])
            turns.append(1)
            return ModelResponse(parts=[TextPart("Your volatility is 25.06%.")])

        result = _agent(script).run_sync("how risky am I?")
        assert result.output == "Your volatility is 25.06%."
        assert len(turns) == 1
