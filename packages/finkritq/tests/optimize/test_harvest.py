# finkrit/packages/finkritq/tests/optimize/test_harvest.py
"""
Tax-loss harvesting candidate scan.

    AAA: 10 @ 100 cost, acquired 2019 (long-term), price 80  -> $200 loss, harvest
    BBB: 10 @ 100 cost, acquired 2023-12-20 (recent),  price 80  -> loss but WASH SALE
    CCC: 10 @ 100 cost, acquired 2019,               price 150 -> a gain, not a candidate

as_of 2024-01-01.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finkritq.optimize import harvest_candidates, long_term_transitions
from finkritq.portfolio import Portfolio, Position, TaxLot
from finkritq.tests.fixtures import make_stock

_AS_OF = date(2024, 1, 1)


def _lot(lot_id: str, cost: str, acquired: date) -> TaxLot:
    return TaxLot(id=lot_id, quantity=Decimal("10"), cost_per_share=Decimal(cost), acquired=acquired)


def _setup():
    aaa, bbb, ccc = make_stock("AAA"), make_stock("BBB"), make_stock("CCC")
    portfolio = Portfolio(
        id="pf",
        name="harvest",
        positions=[
            Position(id="p-aaa", asset=aaa, lots=(_lot("la", "100", date(2019, 1, 1)),)),
            Position(id="p-bbb", asset=bbb, lots=(_lot("lb", "100", date(2023, 12, 20)),)),
            Position(id="p-ccc", asset=ccc, lots=(_lot("lc", "100", date(2019, 1, 1)),)),
        ],
    )
    prices = {aaa: Decimal("80"), bbb: Decimal("80"), ccc: Decimal("150")}
    return portfolio, prices, (aaa, bbb, ccc)


class TestHarvestCandidates:

    def test_flags_the_loss_lot_only(self):
        portfolio, prices, (aaa, _, _) = _setup()
        report = harvest_candidates(portfolio, prices, _AS_OF)
        assert [c.asset for c in report.candidates] == [aaa]
        assert report.candidates[0].unrealized_loss == Decimal("200")
        assert report.candidates[0].is_long_term is True

    def test_wash_sale_blocks_recent_purchase(self):
        portfolio, prices, (_, bbb, _) = _setup()
        report = harvest_candidates(portfolio, prices, _AS_OF)
        assert bbb in report.wash_sale_blocked
        assert all(c.asset is not bbb for c in report.candidates)

    def test_gain_position_is_not_a_candidate(self):
        portfolio, prices, (_, _, ccc) = _setup()
        report = harvest_candidates(portfolio, prices, _AS_OF)
        assert all(c.asset is not ccc for c in report.candidates)

    def test_totals(self):
        portfolio, prices, _ = _setup()
        report = harvest_candidates(portfolio, prices, _AS_OF)
        assert report.total_harvestable_loss == Decimal("200")
        assert report.long_term_loss == Decimal("200")
        assert report.short_term_loss == Decimal("0")

    def test_min_loss_threshold_excludes_small_losses(self):
        portfolio, prices, _ = _setup()
        report = harvest_candidates(portfolio, prices, _AS_OF, min_loss=Decimal("300"))
        assert report.candidates == []          # AAA's $200 loss is below $300
        assert report.total_harvestable_loss == Decimal("0")


class TestLongTermTransitions:
    """
    Boundary countdown, as_of 2024-01-01. TaxLot.is_long_term is
    holding_days >= 365, so a lot acquired D transitions on D + 365 days.

        GGG: acquired 2023-02-01 -> held 334 days, transitions in 31 days, price up
        LLL: acquired 2023-01-20 -> held 346 days, transitions in 19 days, price down
        NNN: acquired 2023-12-01 -> held 31 days, 334 days out, beyond the window
        OOO: acquired 2019      -> already long term, never a countdown
    """

    def _setup(self):
        ggg, lll = make_stock("GGG"), make_stock("LLL")
        nnn, ooo = make_stock("NNN"), make_stock("OOO")
        portfolio = Portfolio(
            id="pf",
            name="countdown",
            positions=[
                Position(id="p-g", asset=ggg, lots=(_lot("lg", "100", date(2023, 2, 1)),)),
                Position(id="p-l", asset=lll, lots=(_lot("ll", "100", date(2023, 1, 20)),)),
                Position(id="p-n", asset=nnn, lots=(_lot("ln", "100", date(2023, 12, 1)),)),
                Position(id="p-o", asset=ooo, lots=(_lot("lo", "100", date(2019, 1, 1)),)),
            ],
        )
        prices = {
            ggg: Decimal("150"),
            lll: Decimal("80"),
            nnn: Decimal("150"),
            ooo: Decimal("150"),
        }
        return portfolio, prices

    def test_only_lots_inside_the_window_report(self):
        portfolio, prices = self._setup()
        rows = long_term_transitions(portfolio, prices, _AS_OF, within_days=45)
        assert [t.asset.ticker for t in rows] == ["LLL", "GGG"]

    def test_sorted_soonest_first(self):
        portfolio, prices = self._setup()
        rows = long_term_transitions(portfolio, prices, _AS_OF, within_days=45)
        assert rows[0].days_until == 19
        assert rows[1].days_until == 31

    def test_transition_date_agrees_with_is_long_term(self):
        # The countdown must flip exactly when TaxLot.is_long_term flips, or a
        # dashboard would advertise a boundary the tax math does not honor.
        portfolio, prices = self._setup()
        for t in long_term_transitions(portfolio, prices, _AS_OF, within_days=45):
            assert not t.lot.is_long_term(t.transition_date - timedelta(days=1))
            assert t.lot.is_long_term(t.transition_date)
            assert (t.transition_date - _AS_OF).days == t.days_until

    def test_gain_is_signed(self):
        portfolio, prices = self._setup()
        by_ticker = {
            t.asset.ticker: t
            for t in long_term_transitions(portfolio, prices, _AS_OF, within_days=45)
        }
        assert by_ticker["GGG"].unrealized_gain == Decimal("500")   # 10 sh, +50
        assert by_ticker["LLL"].unrealized_gain == Decimal("-200")  # 10 sh, -20

    def test_long_term_lot_never_reports(self):
        portfolio, prices = self._setup()
        rows = long_term_transitions(portfolio, prices, _AS_OF, within_days=10_000)
        assert all(t.asset.ticker != "OOO" for t in rows)
