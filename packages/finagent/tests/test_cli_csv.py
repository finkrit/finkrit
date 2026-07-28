# finagent/tests/test_cli_csv.py
"""
Tests for the chat CLI's CSV loader.

One row is one tax lot, so a ticker bought several times must land as several
lots under one position. The web upload path has the same requirement and its
own tests, this covers the terminal path, which parses the file itself rather
than handing it to a model.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finagent.cli import _load_portfolio_from_csv

MULTI_LOT = """ticker,quantity,cost,acquired
AAPL,100,120.00,2021-05-12
MSFT,50,240.00,2021-02-18
AAPL,50,180.00,2023-03-09
AAPL,30,210.00,2024-06-01
"""


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "holdings.csv"
    path.write_text(MULTI_LOT)
    return str(path)


def test_repeated_ticker_becomes_one_position_with_several_lots(csv_path):
    portfolio = _load_portfolio_from_csv(csv_path)
    assert len(portfolio.positions) == 2

    by_ticker = {p.asset.ticker: p for p in portfolio.positions}
    assert len(by_ticker["AAPL"].lots) == 3
    assert len(by_ticker["MSFT"].lots) == 1


def test_each_lot_keeps_its_own_cost_and_date(csv_path):
    portfolio = _load_portfolio_from_csv(csv_path)
    apple = next(p for p in portfolio.positions if p.asset.ticker == "AAPL")

    assert [lot.cost_per_share for lot in apple.lots] == [
        Decimal("120.00"), Decimal("180.00"), Decimal("210.00"),
    ]
    assert [lot.acquired for lot in apple.lots] == [
        date(2021, 5, 12), date(2023, 3, 9), date(2024, 6, 1),
    ]


def test_position_totals_span_the_lots(csv_path):
    portfolio = _load_portfolio_from_csv(csv_path)
    apple = next(p for p in portfolio.positions if p.asset.ticker == "AAPL")
    assert apple.quantity == Decimal("180")


def test_position_order_follows_first_appearance(csv_path):
    portfolio = _load_portfolio_from_csv(csv_path)
    assert [p.asset.ticker for p in portfolio.positions] == ["AAPL", "MSFT"]


def test_lot_ids_are_unique(csv_path):
    portfolio = _load_portfolio_from_csv(csv_path)
    ids = [lot.id for position in portfolio.positions for lot in position.lots]
    assert len(ids) == len(set(ids))


def test_tickers_are_matched_case_insensitively(tmp_path):
    # A file that mixes cases still describes one holding, not two.
    path = tmp_path / "mixed.csv"
    path.write_text("ticker,quantity,cost,acquired\naapl,10,100,2021-01-04\nAAPL,5,120,2022-01-04\n")
    portfolio = _load_portfolio_from_csv(str(path))
    assert len(portfolio.positions) == 1
    assert len(portfolio.positions[0].lots) == 2


class TestRealExportFormatting:
    """A real custodian export is formatted for humans, not for a parser. These
    are the shapes an actual Fidelity lot export arrives in."""

    def test_currency_symbols_and_thousands_separators_are_stripped(self, tmp_path):
        path = tmp_path / "money.csv"
        path.write_text(
            'Symbol,Quantity,Cost Per Share,Date Acquired\n'
            'AAPL,"1,000.000",$120.40,05/12/2021\n'
        )
        portfolio = _load_portfolio_from_csv(str(path))
        lot = portfolio.positions[0].lots[0]
        assert lot.quantity == Decimal("1000.000")
        assert lot.cost_per_share == Decimal("120.40")

    def test_cost_per_share_header_is_recognized(self, tmp_path):
        # The obvious spelling, which the alias list used to miss entirely.
        path = tmp_path / "cps.csv"
        path.write_text("Symbol,Quantity,Cost Per Share,Date Acquired\nMSFT,10,238.60,02/18/2021\n")
        portfolio = _load_portfolio_from_csv(str(path))
        assert portfolio.positions[0].lots[0].cost_per_share == Decimal("238.60")

    def test_us_style_dates_are_parsed(self, tmp_path):
        path = tmp_path / "dates.csv"
        path.write_text("Symbol,Quantity,Cost Per Share,Date Acquired\nKO,10,55.80,10/22/2019\n")
        portfolio = _load_portfolio_from_csv(str(path))
        assert portfolio.positions[0].lots[0].acquired == date(2019, 10, 22)

    def test_extra_columns_are_ignored(self, tmp_path):
        # Description, Term, and the totals ride along and must not confuse the
        # per share cost.
        path = tmp_path / "extra.csv"
        path.write_text(
            "Symbol,Description,Quantity,Date Acquired,Term,Cost Per Share,Cost Basis Total\n"
            'NVDA,NVIDIA CORP,140.000,03/09/2023,Long-term,$168.20,"$23,548.00"\n'
        )
        portfolio = _load_portfolio_from_csv(str(path))
        lot = portfolio.positions[0].lots[0]
        assert lot.cost_per_share == Decimal("168.20")   # not the 23,548 total


def test_an_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("ticker,quantity,cost,acquired\n")
    with pytest.raises(ValueError, match="No holdings found"):
        _load_portfolio_from_csv(str(path))
