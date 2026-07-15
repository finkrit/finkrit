# finkrit/packages/finkritq/portfolio/accountregistration.py
from __future__ import annotations

from dataclasses import dataclass

from finkritq.datatype import AccountRegistrationType


@dataclass(slots=True, frozen=True)
class AccountRegistration:
    """
    Describes the legal ownership/registration of an investment account.
    """

    registration: AccountRegistrationType

    custom_name: str | None = None
    description: str | None = None
    notes: str | None = None

    @property
    def name(self) -> str:
        """Returns the display name for the registration."""
        if self.registration is AccountRegistrationType.OTHER and self.custom_name:
            return self.custom_name

        return self.registration.value

    @property
    def is_custom(self) -> bool:
        return self.registration is AccountRegistrationType.OTHER

    def __str__(self) -> str:
        return self.name

        