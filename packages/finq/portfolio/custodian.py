from __future__ import annotations

from dataclasses import dataclass

from packages.finq.datatype import CustodianType

@dataclass(slots=True)
class Custodian:
    """
    Represents the institution that holds an investment account.
    """

    type: CustodianType
    note: str | None = None

    @property
    def name(self) -> str:
        """
        Display name for the custodian.

        If the type is OTHER and a note is supplied, use the note.
        """
        if self.type is CustodianType.OTHER and self.note:
            return self.note

        return self.type.value

    @property
    def is_custom(self) -> bool:
        return self.type is CustodianType.OTHER
    
