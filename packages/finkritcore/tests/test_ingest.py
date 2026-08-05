# finkritcore/tests/test_ingest.py
"""
The deterministic CSV mapper.

The contract that matters is when it declines. Answering wrongly is worse than
deferring, since a deferral costs a round trip to a model and a wrong answer
becomes someone's portfolio.
"""
from __future__ import annotations

from datetime import date

from finkritcore.ingest import ParsedPortfolio, parse_portfolio_csv_in_code


class TestParsedPortfolioDefaults:

    def test_no_holdings_or_warnings_defaults_empty(self):
        p = ParsedPortfolio(name="Empty")
        assert p.holdings == []
        assert p.warnings == []


class TestParseInCode:
    """The deterministic mapper, which answers before a model is ever built.

    The contract that matters is when it declines. Answering wrongly is worse
    than deferring, since a deferral costs a round trip and a wrong answer
    becomes someone's portfolio.
    """

    def test_a_complete_header_is_answered(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,10,150.0,2023-01-15")
        assert p is not None
        assert p.holdings[0].ticker == "AAPL"
        assert p.holdings[0].quantity == 10
        assert p.holdings[0].cost_per_share == 150.0
        assert str(p.holdings[0].acquired) == "2023-01-15"

    def test_the_name_is_the_caller_s_to_choose(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,1,2,2023-01-15", "Schwab")
        assert p.name == "Schwab"

    def test_a_ticker_is_upper_cased(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\naapl,1,2,2023-01-15")
        assert p.holdings[0].ticker == "AAPL"


class TestParseInCodeDeclines:

    def test_a_missing_field_defers_to_the_model(self):
        # No cost and no date, so the file is genuinely ambiguous.
        assert parse_portfolio_csv_in_code("Symbol,Shares\nAAPL,10") is None

    def test_each_of_the_four_is_load_bearing(self):
        full = {"ticker": "Symbol", "quantity": "Shares",
                "cost_per_share": "Cost", "acquired": "Date"}
        for dropped in full:
            header = ",".join(v for k, v in full.items() if k != dropped)
            row = ",".join("1" for _ in range(len(full) - 1))
            assert parse_portfolio_csv_in_code(f"{header}\n{row}") is None, dropped

    def test_a_complete_header_with_no_usable_row_defers(self):
        # An empty result is not an answer. Letting it through would turn a
        # file we read wrong into a portfolio the user appears to have emptied.
        assert parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\n,,,") is None

    def test_an_empty_file_defers(self):
        assert parse_portfolio_csv_in_code("") is None


class TestParseInCodeGaps:
    """A gap under a column that does exist is noted, not deferred. A model
    cannot recover a value the file never had, so paying for one buys nothing
    the note does not already say."""

    def test_a_blank_cost_is_noted_rather_than_hidden(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,10,,2023-01-15")
        assert p.holdings[0].cost_per_share == 0
        assert "cost per share" in p.holdings[0].confidence_note

    def test_an_unreadable_date_falls_back_to_today(self):
        # Today keeps the lot short term, which never claims a long term rate
        # the holding has not earned.
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,10,150,not-a-date")
        assert p.holdings[0].acquired == date.today()
        assert "acquired date" in p.holdings[0].confidence_note

    def test_several_gaps_land_on_one_note(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,,,zzz")
        note = p.holdings[0].confidence_note
        assert "quantity" in note and "cost per share" in note and "acquired date" in note

    def test_a_clean_row_carries_no_note(self):
        p = parse_portfolio_csv_in_code("Symbol,Shares,Cost,Date\nAAPL,10,150,2023-01-15")
        assert p.holdings[0].confidence_note is None

    def test_skipped_rows_are_counted_not_dropped_silently(self):
        # A totals row, a footer, a blank line. A file that is mostly skipped
        # is a file we read wrong, and the user should be told.
        text = "Symbol,Shares,Cost,Date\nAAPL,10,150,2023-01-15\n,,,\nTotal,,,"
        p = parse_portfolio_csv_in_code(text)
        assert len(p.holdings) == 2   # "Total" has a ticker as far as we can tell
        assert "1 row(s)" in p.warnings[0]


class TestParseInCodeFormatting:
    """What a real export writes, rather than what a clean fixture writes."""

    def test_money_and_thousands_separators_are_stripped(self):
        p = parse_portfolio_csv_in_code(
            'Symbol,Shares,Cost Per Share,Date Acquired\nAAPL,"1,000",$120.40,05/12/2021'
        )
        assert p.holdings[0].quantity == 1000
        assert p.holdings[0].cost_per_share == 120.40
        assert str(p.holdings[0].acquired) == "2021-05-12"

    def test_header_case_and_spacing_do_not_matter(self):
        p = parse_portfolio_csv_in_code("  TICKER , Qty , Avg Cost , Purchase Date \nAAPL,1,2,2023-01-15")
        assert p is not None
        assert p.holdings[0].ticker == "AAPL"

    def test_one_row_is_one_lot_never_merged(self):
        # The separate lots are the whole basis of the tax analytics.
        text = "Symbol,Shares,Cost,Date\nAAPL,10,150,2023-01-15\nAAPL,5,180,2024-03-09"
        p = parse_portfolio_csv_in_code(text)
        assert [h.quantity for h in p.holdings] == [10, 5]
