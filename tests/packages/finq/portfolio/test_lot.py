# finkrit/tests/packages/finq/portfolio/test_lot.py
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from packages.finq.portfolio import Lot


class TestLot:

    @pytest.fixture
    def lot(self, position):
        return Lot(
            id="lot-1",
            position=position,
            quantity=Decimal("10"),
            cost_per_share=Decimal("100"),
            acquired=date.today() - timedelta(days=400),
        )

    def test_asset(self, lot, position):
        assert lot.asset is position.asset

    def test_account(self, lot, position):
        assert lot.account is position.account

    def test_cost_basis(self, lot):
        assert lot.cost_basis == Decimal("1000")

    def test_market_value(self, lot):
        assert lot.market_value(Decimal("120")) == Decimal("1200")

    def test_unrealized_gain_positive(self, lot):
        assert lot.unrealized_gain(Decimal("120")) == Decimal("200")

    def test_unrealized_gain_negative(self, lot):
        assert lot.unrealized_gain(Decimal("80")) == Decimal("-200")

    def test_unrealized_return_positive(self, lot):
        assert lot.unrealized_return(Decimal("120")) == Decimal("0.2")

    def test_unrealized_return_negative(self, lot):
        assert lot.unrealized_return(Decimal("80")) == Decimal("-0.2")

    def test_holding_period(self, lot):
        assert lot.holding_period.days >= 400

    def test_holding_days(self, lot):
        assert lot.holding_days >= 400

    def test_is_long_term_true(self, lot):
        assert lot.is_long_term is True

    def test_is_long_term_false(self, position):
        lot = Lot(
            id="lot-2",
            position=position,
            quantity=Decimal("10"),
            cost_per_share=Decimal("100"),
            acquired=date.today() - timedelta(days=100),
        )
        assert lot.is_long_term is False

    def test_str(self, lot):
        assert str(lot) == "Lot(10 @ 100)"

    def test_repr(self, lot):
        assert repr(lot) == (
            f"Lot(quantity=10, cost_per_share=100, acquired={lot.acquired!r})"
        )

    @pytest.mark.parametrize("quantity", [
        Decimal("0"),
        Decimal("-1"),
    ])
    def test_invalid_quantity(self, position, quantity):
        with pytest.raises(ValueError):
            Lot(
                id="lot",
                position=position,
                quantity=quantity,
                cost_per_share=Decimal("100"),
                acquired=date.today(),
            )

    @pytest.mark.parametrize("cost_per_share", [
        Decimal("0"),
        Decimal("-1"),
    ])
    def test_invalid_cost_per_share(self, position, cost_per_share):
        with pytest.raises(ValueError):
            Lot(
                id="lot",
                position=position,
                quantity=Decimal("10"),
                cost_per_share=cost_per_share,
                acquired=date.today(),
            )

    def test_future_acquired_date(self, position):
        with pytest.raises(ValueError):
            Lot(
                id="lot",
                position=position,
                quantity=Decimal("10"),
                cost_per_share=Decimal("100"),
                acquired=date.today() + timedelta(days=1),
            )

    def test_notes_stored(self, position):
        lot = Lot(
            id="lot",
            position=position,
            quantity=Decimal("10"),
            cost_per_share=Decimal("100"),
            acquired=date.today(),
            notes="Tax lot",
        )
        assert lot.notes == "Tax lot"