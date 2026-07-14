from __future__ import annotations

import pytest

from packages.finq.portfolio.accountregistration import AccountRegistration
from packages.finq.datatype import AccountRegistrationType


class TestAccountRegistration:

    @pytest.mark.parametrize("registration", [
        r for r in AccountRegistrationType
        if r is not AccountRegistrationType.OTHER
    ])
    def test_name_matches_enum_value(self, registration):
        account = AccountRegistration(registration)
        assert account.name == registration.value

    def test_custom_name_used_for_other(self):
        account = AccountRegistration(
            AccountRegistrationType.OTHER,
            custom_name="Family Trust",
        )
        assert account.name == "Family Trust"

    def test_other_without_custom_name_uses_enum_value(self):
        account = AccountRegistration(AccountRegistrationType.OTHER)
        assert account.name == AccountRegistrationType.OTHER.value

    def test_is_custom_true_for_other(self):
        account = AccountRegistration(AccountRegistrationType.OTHER)
        assert account.is_custom is True

    @pytest.mark.parametrize("registration", [
        r for r in AccountRegistrationType
        if r is not AccountRegistrationType.OTHER
    ])
    def test_is_custom_false_for_standard_types(self, registration):
        account = AccountRegistration(registration)
        assert account.is_custom is False

    def test_str_returns_name(self):
        account = AccountRegistration(
            AccountRegistrationType.OTHER,
            custom_name="Retirement Trust",
        )
        assert str(account) == "Retirement Trust"

    def test_fields_are_stored(self):
        account = AccountRegistration(
            registration=AccountRegistrationType.OTHER,
            custom_name="Trust",
            description="Family investment account",
            notes="Opened in 2025",
        )

        assert account.custom_name == "Trust"
        assert account.description == "Family investment account"
        assert account.notes == "Opened in 2025"

    def test_is_frozen(self):
        account = AccountRegistration(AccountRegistrationType.INDIVIDUAL)

        with pytest.raises(AttributeError):
            account.registration = AccountRegistrationType.JOINT