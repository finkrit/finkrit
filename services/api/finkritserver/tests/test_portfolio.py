# finkritserver/tests/test_portfolio.py
"""
Tests for building a finkritq Portfolio from the flat upload shape.

The wire format is one row per tax lot, so a ticker bought several times arrives
as several rows. Those have to land as several lots under ONE Position, because
finkritq's lot analytics read a Position's lots. Splitting them across positions
would leave every holding looking like a single blended lot, with nothing for
harvesting or lot selection to choose between.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from finkritserver.portfolio import build_portfolio
from finkritserver.schemas import HoldingSpec, PortfolioSpec


def _spec(*holdings: HoldingSpec) -> PortfolioSpec:
    return PortfolioSpec(name="Test", holdings=list(holdings))


def _holding(ticker: str, quantity: float, cost: float, acquired: str, **kwargs) -> HoldingSpec:
    return HoldingSpec(
        ticker=ticker, quantity=quantity, cost_per_share=cost,
        acquired=date.fromisoformat(acquired), **kwargs,
    )


class TestLotGrouping:

    def test_repeated_ticker_becomes_one_position_with_several_lots(self):
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("AAPL", 50, 180, "2023-03-09"),
            _holding("AAPL", 30, 210, "2024-06-01"),
        ))
        assert len(portfolio.positions) == 1
        assert len(portfolio.positions[0].lots) == 3

    def test_each_lot_keeps_its_own_cost_and_date(self):
        # The whole point: the purchases must not be merged or averaged.
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("AAPL", 50, 180, "2023-03-09"),
        ))
        lots = portfolio.positions[0].lots
        assert [lot.cost_per_share for lot in lots] == [Decimal("120.0"), Decimal("180.0")]
        assert [lot.acquired for lot in lots] == [date(2021, 5, 12), date(2023, 3, 9)]

    def test_position_totals_span_the_lots(self):
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("AAPL", 50, 180, "2023-03-09"),
        ))
        position = portfolio.positions[0]
        assert position.quantity == Decimal("150")
        assert position.cost_basis == Decimal("100") * Decimal("120") + Decimal("50") * Decimal("180")

    def test_distinct_tickers_stay_separate(self):
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("MSFT", 50, 240, "2021-02-18"),
        ))
        assert [p.asset.ticker for p in portfolio.positions] == ["AAPL", "MSFT"]
        assert all(len(p.lots) == 1 for p in portfolio.positions)

    def test_position_order_follows_first_appearance(self):
        # Not alphabetical, and not the order the grouping happened to produce.
        portfolio = build_portfolio(_spec(
            _holding("MSFT", 50, 240, "2021-02-18"),
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("MSFT", 25, 300, "2023-01-05"),
        ))
        assert [p.asset.ticker for p in portfolio.positions] == ["MSFT", "AAPL"]

    def test_same_ticker_on_a_different_exchange_is_a_different_holding(self):
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12", exchange="NASDAQ"),
            _holding("AAPL", 100, 120, "2021-05-12", exchange="NYSE"),
        ))
        assert len(portfolio.positions) == 2

    def test_lot_ids_are_unique(self):
        # A position with several lots cannot key them all off the ticker.
        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),
            _holding("AAPL", 50, 180, "2023-03-09"),
            _holding("MSFT", 50, 240, "2021-02-18"),
        ))
        ids = [lot.id for position in portfolio.positions for lot in position.lots]
        assert len(ids) == len(set(ids))


class TestHarvestingSeesTheLots:

    def test_underwater_lots_are_found_behind_a_profitable_position(self):
        # A position can be up overall while individual lots are down. Blending
        # them into one lot hides exactly the losses worth harvesting.
        from finkritq.optimize.harvest import harvest_candidates

        portfolio = build_portfolio(_spec(
            _holding("AAPL", 100, 120, "2021-05-12"),   # up at 150
            _holding("AAPL", 50, 180, "2023-03-09"),    # down at 150
            _holding("AAPL", 30, 210, "2024-06-01"),    # down at 150
        ))
        prices = {portfolio.positions[0].asset: Decimal("150")}
        report = harvest_candidates(portfolio, prices, date(2024, 9, 1))

        assert len(report.candidates) == 2
        assert report.total_harvestable_loss == Decimal("3300")

    def test_losses_split_by_holding_period(self):
        from finkritq.optimize.harvest import harvest_candidates

        portfolio = build_portfolio(_spec(
            _holding("AAPL", 50, 180, "2023-03-09"),   # long term by the as-of date
            _holding("AAPL", 30, 210, "2024-06-01"),   # short term
        ))
        prices = {portfolio.positions[0].asset: Decimal("150")}
        report = harvest_candidates(portfolio, prices, date(2024, 9, 1))

        assert report.long_term_loss == Decimal("1500")
        assert report.short_term_loss == Decimal("1800")
