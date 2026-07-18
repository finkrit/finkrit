# finkrit/packages/finkritq/portfolio/account.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterator

from finkritq.asset.asset import Asset
from finkritq.datatype import (
    AccountRegistrationType,
    Currency,
)
from finkritq.portfolio.custodian import Custodian
from finkritq.portfolio.position import Position


@dataclass(slots=True, eq=False)
class Account:
    """
    Represents an investment account held at a custodian.

    ``eq=False`` -> identity equality (an Account is a mutable entity, not a
    value; see Position for the rationale).
    """

    id: str
    account_number: str
    name: str

    custodian: Custodian
    account_registration_type: AccountRegistrationType

    nickname: str | None = None
    base_currency: Currency = Currency.USD

    is_closed: bool = False
    opened_on: date | None = None
    closed_on: date | None = None

    positions: list[Position] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        if self.closed_on and not self.is_closed:
            raise ValueError("closed_on cannot be set unless is_closed=True.")

        if self.opened_on and self.closed_on and self.closed_on < self.opened_on:
            raise ValueError("closed_on cannot be before opened_on.")

    # ------------------------------------------------------------------
    # Position Management
    # ------------------------------------------------------------------

    def add_position(self, position: Position) -> Position:
        """
        Adds a position to the account.

        If the account already holds the asset, the incoming position's lots
        are MERGED into the existing position (a second purchase of the same
        asset is another tax lot, not a duplicate to discard). Returns the
        resulting position. Previously this silently dropped the new lots.
        """
        existing = self.get_position(position.asset)

        if existing is not None:
            # Idempotent re-add of the same object -> no-op. A *different*
            # position for an already-held asset contributes its lots (a second
            # purchase is another tax lot, not a duplicate to discard).
            if existing is not position:
                existing.lots = existing.lots + position.lots
            return existing

        self.positions.append(position)
        return position

    def remove_position(self, asset: Asset) -> Position | None:
        """
        Removes and returns the position for the asset.
        """
        position = self.get_position(asset)

        if position is None:
            return None

        self.positions.remove(position)
        return position

    def get_position(self, asset: Asset) -> Position | None:
        """
        Returns the position for the asset.
        """
        return next((p for p in self.positions if p.asset == asset), None)

    def has_position(self, asset: Asset) -> bool:
        """
        Returns True if the account contains the asset.
        """
        return self.get_position(asset) is not None

    # ------------------------------------------------------------------
    # Derived Properties
    # ------------------------------------------------------------------

    @property
    def assets(self) -> list[Asset]:
        return [p.asset for p in self.positions]

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def market_value(self) -> Decimal:
        return sum((p.market_value for p in self.positions), start=Decimal("0"))

    @property
    def cost_basis(self) -> Decimal:
        return sum((p.cost_basis for p in self.positions), start=Decimal("0"))

    @property
    def unrealized_gain(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def is_empty(self) -> bool:
        return not self.positions

    # ------------------------------------------------------------------
    # Collection Interface
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[Position]:
        return iter(self.positions)

    def __len__(self) -> int:
        return len(self.positions)

    def __contains__(self, asset: Asset) -> bool:
        return self.has_position(asset)

    def __str__(self) -> str:
        return self.nickname or self.name
    
