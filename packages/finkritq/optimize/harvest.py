# finkrit/packages/finkritq/optimize/harvest.py
"""
Tax-loss harvesting: scan a portfolio's lots for unrealized losses worth
realizing, a core feature of tax-managed platforms.

A lot is a candidate if its unrealized loss clears a threshold AND harvesting it
would not trip the wash-sale rule. This is the *single-portfolio* version: the
wash-sale check looks only within this portfolio (was the same asset bought
within the window). The correct cross-account, cross-registration wash-sale check
needs the ownership graph and is the no part of this deliberately.

Pure lots + prices, no org graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from finkritq.asset import Asset
from finkritq.portfolio import Portfolio, TaxLot


@dataclass(frozen=True, slots=True)
class HarvestCandidate:
    """One lot worth harvesting: its loss (a positive magnitude) and tax
    character."""

    asset: Asset
    lot: TaxLot
    current_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    unrealized_loss: Decimal   # positive magnitude of the loss
    is_long_term: bool


@dataclass(frozen=True, slots=True)
class HarvestReport:
    candidates: list[HarvestCandidate]
    total_harvestable_loss: Decimal
    short_term_loss: Decimal
    long_term_loss: Decimal
    wash_sale_blocked: tuple[Asset, ...]   # assets skipped due to a recent buy


@dataclass(frozen=True, slots=True)
class LongTermTransition:
    """
    One short term lot approaching the long-term boundary.

    ``unrealized_gain`` is signed: the boundary cuts both ways. A
    gain lot is worth holding until the transition (the gain gets the long term
    rate), a loss lot is worth harvesting before it (a short term loss offsets
    the higher-taxed short term gains first).This module reports the facts, the 
    caller decides the action.
    """

    asset: Asset
    lot: TaxLot
    current_price: Decimal
    market_value: Decimal
    unrealized_gain: Decimal   # signed: positive is a gain, negative a loss
    transition_date: date      # first day the lot counts as long term
    days_until: int            # from as_of, always >= 1


def long_term_transitions(
        portfolio: Portfolio,
        prices: dict[Asset, Decimal],
        as_of: date,
        within_days: int = 45,
    ) -> list[LongTermTransition]:
    """
    Short term lots that become long term within ``within_days`` of ``as_of``.

    The transition date mirrors TaxLot.is_long_term (holding_days >= 365), so
    a lot transitions on ``acquired + 365 days`` and the countdown agrees with
    every other long/short split in the package. Sorted soonest first, ties
    broken by market value so the money at stake surfaces before dust.
    """
    transitions: list[LongTermTransition] = []
    for position in portfolio.positions:
        asset = position.asset
        price = prices[asset]
        for lot in position.lots:
            if lot.is_long_term(as_of):
                continue
            days_until = 365 - lot.holding_days(as_of)
            if days_until > within_days:
                continue
            market_value = lot.market_value(price)
            transitions.append(
                LongTermTransition(
                    asset=asset,
                    lot=lot,
                    current_price=price,
                    market_value=market_value,
                    unrealized_gain=market_value - lot.cost_basis,
                    transition_date=lot.acquired + timedelta(days=365),
                    days_until=days_until,
                )
            )

    transitions.sort(key=lambda t: (t.days_until, -t.market_value))
    return transitions


def _recently_purchased(lots: tuple[TaxLot, ...], as_of: date, window_days: int) -> bool:
    # Wash-sale trigger (single-portfolio): the same asset was bought within the
    # window on or before the sale date. Purchases after the sale cannot be known
    # from holdings alone, so only the trailing side is checked here.
    return any(0 <= (as_of - lot.acquired).days <= window_days for lot in lots)


def harvest_candidates(
    portfolio: Portfolio,
    prices: dict[Asset, Decimal],
    as_of: date,
    min_loss: Decimal = Decimal("0"),
    wash_sale_window_days: int = 30,
) -> HarvestReport:
    """
    Find lots worth harvesting at the given prices.

    A lot qualifies when its unrealized loss (cost basis minus market value)
    exceeds ``min_loss``. An asset with any lot bought within
    ``wash_sale_window_days`` of ``as_of`` is skipped entirely (harvesting it
    would be a wash sale) and reported in ``wash_sale_blocked``. Losses are split
    short/long-term by holding period as of ``as_of``.
    """
    candidates: list[HarvestCandidate] = []
    short_term = Decimal("0")
    long_term = Decimal("0")
    blocked: list[Asset] = []

    for position in portfolio.positions:
        asset = position.asset
        price = prices[asset]

        if _recently_purchased(position.lots, as_of, wash_sale_window_days):
            blocked.append(asset)
            continue

        for lot in position.lots:
            market_value = lot.quantity * price
            loss = lot.cost_basis - market_value   # positive => a loss
            if loss <= min_loss:
                continue

            is_long_term = lot.is_long_term(as_of)
            candidates.append(
                HarvestCandidate(
                    asset=asset,
                    lot=lot,
                    current_price=price,
                    market_value=market_value,
                    cost_basis=lot.cost_basis,
                    unrealized_loss=loss,
                    is_long_term=is_long_term,
                )
            )
            if is_long_term:
                long_term += loss
            else:
                short_term += loss

    # Biggest losses first, the harvest an operator acts on first.
    candidates.sort(key=lambda c: c.unrealized_loss, reverse=True)

    return HarvestReport(
        candidates=candidates,
        total_harvestable_loss=short_term + long_term,
        short_term_loss=short_term,
        long_term_loss=long_term,
        wash_sale_blocked=tuple(blocked),
    )
