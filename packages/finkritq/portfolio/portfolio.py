# finkrit/packages/finkritq/portfolio/portfolio.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Iterator

from packages.finkritq.asset import Asset
from packages.finkritq.portfolio.account import Account
from packages.finkritq.portfolio.lot import Lot
from packages.finkritq.portfolio.position import Position


@dataclass(slots=True)
class Portfolio:
    """
    Represents a collection of investment accounts managed together.
    """

    id: str
    name: str

    accounts: list[Account] = field(default_factory=list)

    # Higher-level objects (RIA platform)
    user: Any | None = None
    
    notes: str | None = None

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    def add_account(self, account: Account) -> Account:
        existing = self.get_account(account.id)

        if existing is not None:
            return existing

        self.accounts.append(account)
        return account

    def remove_account(self, account_id: str) -> Account | None:
        account = self.get_account(account_id)

        if account is None:
            return None

        self.accounts.remove(account)
        return account

    def get_account(self, account_id: str) -> Account | None:
        return next((a for a in self.accounts if a.id == account_id), None)

    def has_account(self, account_id: str) -> bool:
        return self.get_account(account_id) is not None

    # ------------------------------------------------------------------
    # Derived Collections
    # ------------------------------------------------------------------

    @property
    def positions(self) -> tuple[Position, ...]:
        return tuple(
            position
            for account in self.accounts
            for position in account
        )

    @property
    def assets(self) -> tuple[Asset, ...]:
        return tuple(position.asset for position in self.positions)

    @property
    def lots(self) -> tuple[Lot, ...]:
        return tuple(
            lot
            for position in self.positions
            for lot in position.lots
        )

    # ------------------------------------------------------------------
    # Aggregate Properties
    # ------------------------------------------------------------------

    @property
    def cost_basis(self) -> Decimal:
        return sum((account.cost_basis for account in self.accounts), start=Decimal("0"))

    @property
    def account_count(self) -> int:
        return len(self.accounts)

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    @property
    def lot_count(self) -> int:
        return len(self.lots)

    @property
    def is_empty(self) -> bool:
        return not self.accounts

    @property
    def long_term_lots(self) -> tuple[Lot, ...]:
        return tuple(lot for lot in self.lots if lot.is_long_term)

    @property
    def short_term_lots(self) -> tuple[Lot, ...]:
        return tuple(lot for lot in self.lots if not lot.is_long_term)

    @property
    def earliest_acquired(self) -> date:
        return min(lot.acquired for lot in self.lots)

    @property
    def latest_acquired(self) -> date:
        return max(lot.acquired for lot in self.lots)

    # ------------------------------------------------------------------
    # Collection Interface
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[Account]:
        return iter(self.accounts)

    def __len__(self) -> int:
        return len(self.accounts)

    def __contains__(self, account: Account) -> bool:
        return account in self.accounts

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (
            f"Portfolio("
            f"name={self.name!r}, "
            f"accounts={self.account_count}, "
            f"positions={self.position_count})"
        )
    
