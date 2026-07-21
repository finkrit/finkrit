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
