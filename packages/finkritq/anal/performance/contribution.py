# finkrit/packages/finkritq/anal/performance/contribution.py
"""
Contribution to return: how much each holding added to or subtracted from the
portfolio's total return over the window, the "top contributors and detractors"
line every performance report carries.

This is the plain-language companion to attribution. Attribution is
benchmark-relative (allocation vs selection), contribution is absolute: on a
buy-and-hold basis each holding's contribution is its START weight times its own
total return, and those pieces sum exactly to the portfolio's total return (the
value path holds today's share counts fixed, so there is no rebalancing term to
reconcile). Rank them and the ends of the list are the contributors and
detractors.
"""
from __future__ import annotations

from dataclasses import dataclass

from finkritq.asset import Asset
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class Contribution:
    """One holding's contribution to the portfolio's total return."""

    asset: Asset
    start_weight: float     # weight at the start of the window
    asset_return: float     # the asset's own total return over the window
    contribution: float     # start_weight * asset_return


def contribution_to_return(portfolio_data: PortfolioData) -> list[Contribution]:
    """
    Each holding's contribution to total return, ranked best first.

    ``contribution = start_weight * asset_return``. Summed across holdings this
    equals the portfolio's total return over the window. The first entries are the
    top contributors, the last are the detractors.
    """
    start_weights = portfolio_data.start_weights

    contributions: list[Contribution] = []
    for asset, weight in start_weights.items():
        close = portfolio_data[asset].close
        asset_return = float(close[-1] / close[0] - 1.0)
        contributions.append(Contribution(
            asset=asset,
            start_weight=weight,
            asset_return=asset_return,
            contribution=weight * asset_return,
        ))

    contributions.sort(key=lambda item: item.contribution, reverse=True)
    return contributions
