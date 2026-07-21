# finkrit/packages/finkritq/tests/optimize/test_harvest.py
"""
Tax-loss harvesting candidate scan.

    AAA: 10 @ 100 cost, acquired 2019 (long-term), price 80  -> $200 loss, harvest
    BBB: 10 @ 100 cost, acquired 2023-12-20 (recent),  price 80  -> loss but WASH SALE
    CCC: 10 @ 100 cost, acquired 2019,               price 150 -> a gain, not a candidate

as_of 2024-01-01.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from finkritq.optimize import harvest_candidates
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
