# finkrit/tests/packages/finkritq/portfolio/test_position.py
"""
Position after the de-cycle (D-0): constructs normally (no __new__ dance, no
account back-reference), and uses identity equality (mutable entity).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finkritq.portfolio import Position, TaxLot
from finkritq.tests.fixtures import make_stock


def _lot(qty="10", lot_id="lot-1") -> TaxLot:
    return TaxLot(id=lot_id, quantity=Decimal(qty), cost_per_share=Decimal("100"), acquired=date(2020, 1, 1))


class TestPositionConstruction:

    def test_constructs_with_plain_constructor(self):
        # The whole point of de-cycling: no Position.__new__, no account arg.
        pos = Position(id="p1", asset=make_stock("AAA"), lots=(_lot(),))
        assert pos.id == "p1"
        assert pos.asset == make_stock("AAA")
        assert pos.quantity == Decimal("10")

    def test_requires_at_least_one_lot(self):
        with pytest.raises(ValueError):
            Position(id="p1", asset=make_stock("AAA"), lots=())

    def test_multiple_lots_aggregate_quantity(self):
        pos = Position(id="p1", asset=make_stock("AAA"), lots=(_lot("10", "l1"), _lot("5", "l2")))
        assert pos.quantity == Decimal("15")

    def test_has_no_account_attribute(self):
        pos = Position(id="p1", asset=make_stock("AAA"), lots=(_lot(),))
        assert not hasattr(pos, "account")


class TestPositionIdentity:

    def test_two_positions_with_identical_contents_are_not_equal(self):
        # eq=False -> identity semantics; distinct entities aren't "equal".
        a = Position(id="p1", asset=make_stock("AAA"), lots=(_lot(),))
        b = Position(id="p1", asset=make_stock("AAA"), lots=(_lot(),))
        assert a != b
        assert a == a

    def test_no_recursion_error_on_equality(self):
        # The old cyclic graph blew the stack on value-equality of reconstructed
        # objects. Identity equality can't recurse.
        a = Position(id="p1", asset=make_stock("AAA"), lots=(_lot(),))
        b = Position(id="p2", asset=make_stock("BBB"), lots=(_lot(),))
        assert (a == b) is False  # returns cleanly, no RecursionError
