# finkrit/tests/packages/finkritq/portfolio/test_account.py
from __future__ import annotations

from datetime import date

import pytest

from finkritq.datatype import AccountRegistrationType, Currency
from finkritq.portfolio.account import Account


from datetime import date

import pytest

from finkritq.portfolio import Account


class TestAccount:

    def test_optional_fields_stored(self, custodian):
        account = Account(
            id="1",
            account_number="12345",
            name="Brokerage",
            custodian=custodian,
            account_registration_type=AccountRegistrationType.JOINT,
            nickname="Taxable",
            base_currency=Currency.CAD,
            is_closed=True,
            opened_on=date(2020, 1, 1),
            closed_on=date(2025, 1, 1),
        )

        assert account.custodian is custodian
        assert account.account_registration_type is AccountRegistrationType.JOINT
        assert account.nickname == "Taxable"
        assert account.base_currency is Currency.CAD
        assert account.is_closed is True
        assert account.opened_on == date(2020, 1, 1)
        assert account.closed_on == date(2025, 1, 1)

    def test_add_position(self, account, position):
        returned = account.add_position(position)

        assert returned is position
        assert account.position_count == 1
        assert position in account.positions

    def test_add_duplicate_position_returns_existing(self, account, position):
        account.add_position(position)

        returned = account.add_position(position)

        assert returned is position
        assert account.position_count == 1

    def test_remove_position(self, account, position):
        account.add_position(position)

        removed = account.remove_position(position.asset)

        assert removed is position
        assert account.position_count == 0

    def test_remove_missing_position_returns_none(self, account, asset):
        assert account.remove_position(asset) is None

    def test_get_position(self, account, position):
        account.add_position(position)

        assert account.get_position(position.asset) is position

    def test_get_missing_position_returns_none(self, account, asset):
        assert account.get_position(asset) is None

    def test_has_position_true(self, account, position):
        account.add_position(position)

        assert account.has_position(position.asset)

    def test_has_position_false(self, account, asset):
        assert not account.has_position(asset)

    def test_assets(self, account, position):
        account.add_position(position)

        assert account.assets == [position.asset]

    def test_position_count(self, account, position):
        assert account.position_count == 0

        account.add_position(position)

        assert account.position_count == 1

    def test_market_value(self, account, position):
        account.add_position(position)

        assert account.market_value == position.market_value

    def test_cost_basis(self, account, position):
        account.add_position(position)

        assert account.cost_basis == position.cost_basis

    def test_unrealized_gain(self, account, position):
        account.add_position(position)

        assert account.unrealized_gain == (
            position.market_value - position.cost_basis
        )

    def test_is_empty_true(self, account):
        assert account.is_empty

    def test_is_empty_false(self, account, position):
        account.add_position(position)

        assert not account.is_empty

    def test_iter(self, account, position):
        account.add_position(position)

        assert list(account) == [position]

    def test_len(self, account, position):
        assert len(account) == 0

        account.add_position(position)

        assert len(account) == 1

    def test_contains(self, account, position):
        account.add_position(position)

        assert position.asset in account

    def test_not_contains(self, account, asset):
        assert asset not in account

    def test_str_uses_nickname(self, account):
        account.nickname = "Brokerage"

        assert str(account) == "Brokerage"

    def test_str_uses_name_when_no_nickname(self, account):
        account.nickname = None

        assert str(account) == account.name

    def test_closed_on_requires_closed_account(self, custodian):
        with pytest.raises(
            ValueError,
            match="closed_on cannot be set unless is_closed=True",
        ):
            Account(
                id="1",
                account_number="123",
                name="Account",
                custodian=custodian,
                account_registration_type=AccountRegistrationType.INDIVIDUAL,
                closed_on=date.today(),
            )

    def test_closed_before_opened_raises(self, custodian):
        with pytest.raises(
            ValueError,
            match="closed_on cannot be before opened_on",
        ):
            Account(
                id="1",
                account_number="123",
                name="Account",
                custodian=custodian,
                account_registration_type=AccountRegistrationType.INDIVIDUAL,
                is_closed=True,
                opened_on=date(2025, 1, 2),
                closed_on=date(2025, 1, 1),
            )

