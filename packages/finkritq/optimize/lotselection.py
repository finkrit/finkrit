# finkrit/packages/finkritq/optimize/lotselection.py
"""
Tax-aware lot selection: given that we must sell some quantity of a position,
choose *which* tax lots to realize so as to control the tax hit.

This is the lot-level engine underneath rebalancing and harvesting. Tax-managed
platforms lead with HIFO (highest-cost lots first), because at a single sale price
that realizes the smallest gain (or the largest loss). The result splits the
realized gain into short- and long-term, since they are taxed differently.

Pure lot math, no org graph, it needs cost basis, acquired dates, and a price,
nothing about who owns the account or where it custodies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from finkritq.portfolio import Position, TaxLot


class LotSaleMethod(Enum):
    FIFO = "fifo"   # oldest acquired first (the IRS default)
    LIFO = "lifo"   # newest acquired first
    HIFO = "hifo"   # highest cost-per-share first -> minimizes realized gain


@dataclass(frozen=True, slots=True)
class RealizedLot:
    """A (possibly partial) sale out of one tax lot."""

    lot: TaxLot
    quantity_sold: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    is_long_term: bool

    @property
    def gain(self) -> Decimal:
        return self.proceeds - self.cost_basis


@dataclass(frozen=True, slots=True)
class SaleResult:
    """The full set of lot sales realizing a requested quantity, with the tax
    split callers actually budget against."""

    realized_lots: list[RealizedLot]
    quantity_sold: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    short_term_gain: Decimal
    long_term_gain: Decimal

    @property
    def realized_gain(self) -> Decimal:
        return self.short_term_gain + self.long_term_gain


def _ordered_lots(lots: tuple[TaxLot, ...], method: LotSaleMethod) -> list[TaxLot]:
    if method is LotSaleMethod.FIFO:
        return sorted(lots, key=lambda lot: lot.acquired)
    if method is LotSaleMethod.LIFO:
        return sorted(lots, key=lambda lot: lot.acquired, reverse=True)
    # HIFO: highest cost per share first
    return sorted(lots, key=lambda lot: lot.cost_per_share, reverse=True)


def select_lots_to_sell(
    position: Position,
    quantity: Decimal,
    price: Decimal,
    as_of: date,
    method: LotSaleMethod = LotSaleMethod.HIFO,
) -> SaleResult:
    """
    Choose lots to sell ``quantity`` shares of ``position`` at ``price``, under a
    lot-ordering ``method``. Lots are consumed in the method's order, splitting the
    last lot if needed. Selling more than is held raises.

    HIFO (the default) minimizes realized gain at a single price. Long/short-term
    is decided per lot by its holding period as of ``as_of`` (the 365-day rule),
    so the caller can budget against short- and long-term gains separately.
    """
    if quantity <= 0:
        raise ValueError("quantity to sell must be positive.")
    if quantity > position.quantity:
        raise ValueError(
            f"cannot sell {quantity} shares, position holds {position.quantity}."
        )

    remaining = quantity
    realized: list[RealizedLot] = []
    short_term = Decimal("0")
    long_term = Decimal("0")
    total_proceeds = Decimal("0")
    total_cost = Decimal("0")

    for lot in _ordered_lots(position.lots, method):
        if remaining <= 0:
            break

        take = min(lot.quantity, remaining)
        proceeds = take * price
        cost = take * lot.cost_per_share
        is_long_term = lot.is_long_term(as_of)

        realized.append(
            RealizedLot(
                lot=lot,
                quantity_sold=take,
                proceeds=proceeds,
                cost_basis=cost,
                is_long_term=is_long_term,
            )
        )
        gain = proceeds - cost
        if is_long_term:
            long_term += gain
        else:
            short_term += gain
        total_proceeds += proceeds
        total_cost += cost
        remaining -= take

    return SaleResult(
        realized_lots=realized,
        quantity_sold=quantity,
        proceeds=total_proceeds,
        cost_basis=total_cost,
        short_term_gain=short_term,
        long_term_gain=long_term,
    )

