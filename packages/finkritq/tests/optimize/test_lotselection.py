# finkrit/packages/finkritq/tests/optimize/test_lotselection.py
"""
Tax-aware lot selection. Three lots with costs and dates chosen so FIFO, LIFO,
and HIFO each pick a different set, making every realized gain hand-checkable.

    lot A: 10 @ 100, acquired 2019-01-01  (long-term)
    lot B: 10 @ 150, acquired 2020-01-01  (long-term)
    lot C: 10 @  80, acquired 2023-09-01  (short-term as of 2024-01-01)

Sell 15 shares at price 120, as_of 2024-01-01.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finkritq.optimize import LotSaleMethod, select_lots_to_sell
from finkritq.portfolio import Position, TaxLot
from finkritq.tests.fixtures import make_stock

_AS_OF = date(2024, 1, 1)
_PRICE = Decimal("120")


def _position() -> Position:
    lots = (
        TaxLot(id="A", quantity=Decimal("10"), cost_per_share=Decimal("100"), acquired=date(2019, 1, 1)),
        TaxLot(id="B", quantity=Decimal("10"), cost_per_share=Decimal("150"), acquired=date(2020, 1, 1)),
        TaxLot(id="C", quantity=Decimal("10"), cost_per_share=Decimal("80"), acquired=date(2023, 9, 1)),
    )
    return Position(id="p", asset=make_stock("AAA"), lots=lots)


def _sell(method: LotSaleMethod):
    return select_lots_to_sell(_position(), Decimal("15"), _PRICE, _AS_OF, method=method)


class TestHIFO:
    # Highest cost first: B (150) full, then A (100) for 5. Both long-term.
    def test_realizes_smallest_gain(self):
        r = _sell(LotSaleMethod.HIFO)
        assert r.realized_gain == Decimal("-200")   # B: -300, A: +100
        assert r.short_term_gain == Decimal("0")
        assert r.long_term_gain == Decimal("-200")

    def test_lots_consumed_in_order(self):
        r = _sell(LotSaleMethod.HIFO)
        assert [rl.lot.id for rl in r.realized_lots] == ["B", "A"]
        assert r.realized_lots[0].quantity_sold == Decimal("10")
        assert r.realized_lots[1].quantity_sold == Decimal("5")


class TestFIFO:
    # Oldest first: A full, then B for 5. Both long-term.
    def test_gain(self):
        r = _sell(LotSaleMethod.FIFO)
        assert r.realized_gain == Decimal("50")      # A: +200, B: -150
        assert r.long_term_gain == Decimal("50")
        assert r.short_term_gain == Decimal("0")


class TestLIFO:
    # Newest first: C full (short-term), then B for 5 (long-term).
    def test_splits_short_and_long_term(self):
        r = _sell(LotSaleMethod.LIFO)
        assert r.short_term_gain == Decimal("400")   # C: +400 short-term
        assert r.long_term_gain == Decimal("-150")   # B: -150 long-term
        assert r.realized_gain == Decimal("250")


class TestInvariants:

    def test_hifo_never_realizes_more_gain_than_fifo(self):
        assert _sell(LotSaleMethod.HIFO).realized_gain <= _sell(LotSaleMethod.FIFO).realized_gain

    def test_quantity_and_proceeds(self):
        r = _sell(LotSaleMethod.HIFO)
        assert r.quantity_sold == Decimal("15")
        assert r.proceeds == Decimal("15") * _PRICE

    def test_oversell_raises(self):
        with pytest.raises(ValueError):
            select_lots_to_sell(_position(), Decimal("31"), _PRICE, _AS_OF)

    def test_nonpositive_quantity_raises(self):
        with pytest.raises(ValueError):
            select_lots_to_sell(_position(), Decimal("0"), _PRICE, _AS_OF)


class TestSellWithinGain:
    """The partial-fill primitive: sell up to a quantity without realizing more
    than a gain budget, consuming a strict prefix of the method's lot order.

    At price 120: lot A gains 20/share, lot B loses 30/share, lot C gains
    40/share. Every expected figure is hand-checkable from those three rates."""

    def _sell(self, quantity, max_gain, method=LotSaleMethod.HIFO):
        from finkritq.optimize import select_lots_to_sell_within_gain
        return select_lots_to_sell_within_gain(
            _position(), Decimal(quantity), _PRICE, _AS_OF,
            max_gain=Decimal(max_gain), method=method,
        )

    def test_room_bigger_than_the_sale_changes_nothing(self):
        # HIFO order B, A, C. Selling 15 realizes B fully (-300) then 5 of A
        # (+100), net -200. Any room above that nets identically to the
        # unconstrained selector.
        unconstrained = _sell(LotSaleMethod.HIFO)
        capped = self._sell("15", "1000")
        assert capped.quantity_sold == Decimal("15")
        assert capped.realized_gain == unconstrained.realized_gain

    def test_truncates_inside_a_gain_lot_to_exactly_the_room(self):
        # HIFO, sell 25: B fully (-300), A fully (+200), then C at +40/share.
        # Room 0 after B+A leaves -100 of room... net so far is -100, so room
        # remaining for C is max_gain - (-100). With max_gain=0 the walk can
        # afford 100/40 = 2.5 shares of C.
        result = self._sell("25", "0")
        assert result.quantity_sold == Decimal("22.5")
        assert result.realized_gain == Decimal("0")
        assert [r.lot.id for r in result.realized_lots] == ["B", "A", "C"]
        assert result.realized_lots[-1].quantity_sold == Decimal("2.5")

    def test_zero_room_against_a_pure_gain_front_sells_nothing(self):
        # FIFO order A, C, B. A gains from the first share, so zero room means
        # zero shares, the caller reads that as a full deferral.
        result = self._sell("15", "0", method=LotSaleMethod.FIFO)
        assert result.quantity_sold == Decimal("0")
        assert result.realized_lots == []

    def test_prefix_rule_never_skips_ahead_to_a_later_loss_lot(self):
        # FIFO order is A, B, C by acquired date. Sell 25 with room 150: A gains
        # 20/share, so only 7.5 of its 10 shares fit, and the walk STOPS there.
        # B's losses sit right behind and would refill the room, but reaching
        # them means realizing lots out of the elected order.
        result = self._sell("25", "150", method=LotSaleMethod.FIFO)
        assert [r.lot.id for r in result.realized_lots] == ["A"]
        assert result.quantity_sold == Decimal("7.5")
        assert result.realized_gain == Decimal("150")

    def test_a_loss_lot_between_gain_lots_extends_the_fill(self):
        # Same FIFO order with room 250: A fits fully (+200, room 50), B is a
        # loss lot taken whole (-300, room 350), and C fits entirely. The
        # elected order is honored AND the budget stretches, no skipping needed.
        result = self._sell("25", "250", method=LotSaleMethod.FIFO)
        assert [r.lot.id for r in result.realized_lots] == ["A", "B", "C"]
        assert result.quantity_sold == Decimal("25")
        assert result.realized_gain == Decimal("100")

    def test_a_loss_lot_refills_the_room(self):
        # HIFO, sell 30 (everything), room 50: B (-300) then A (+200) nets
        # -100, so C can take (50+100)/40 = 3.75 shares. Total 23.75.
        result = self._sell("30", "50")
        assert result.quantity_sold == Decimal("23.75")
        assert result.realized_gain == Decimal("50")

    def test_rejects_nonpositive_and_oversized_quantity(self):
        with pytest.raises(ValueError):
            self._sell("0", "100")
        with pytest.raises(ValueError):
            self._sell("31", "100")
