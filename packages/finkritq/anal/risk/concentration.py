# finkrit/packages/finkritq/anal/risk/concentration.py
"""
Concentration and exposure: the "how and what of my exposure" view.

Concentration measures how much of the portfolio rides on a few positions
(single-name risk), and exposure buckets weights by a grouping (sector, asset
class, region, factor). Both derive from the portfolio's current weights, so they
need no return history, just the composition.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Hashable

from finkritq.asset import Asset
from finkritq.portfolio import PortfolioData


def herfindahl_index(weights: Sequence[float]) -> float:
    """
    Herfindahl-Hirschman index: sum of squared weights. Ranges from 1/n (perfectly
    equal-weighted across n holdings) to 1 (everything in one name). The standard
    single-number concentration measure.
    """
    return float(sum(w * w for w in weights))


def effective_holdings(weights: Sequence[float]) -> float:
    """
    Effective number of holdings: 1 / HHI. An equal-weighted 10-stock portfolio has
    10 effective holdings, a portfolio dominated by one name has close to 1. A more
    intuitive read of the same information as the HHI.
    """
    hhi = herfindahl_index(weights)
    return 1.0 / hhi if hhi > 0 else 0.0


def concentration_ratio(weights: Sequence[float], n: int) -> float:
    """Fraction of the portfolio held in its ``n`` largest positions."""
    return float(sum(sorted(weights, reverse=True)[:n]))


def max_weight(weights: Sequence[float]) -> float:
    return max(weights, default=0.0)


def exposure_by_group(
    weights: dict[Asset, float],
    group_of: Callable[[Asset], Hashable],
) -> dict[Hashable, float]:
    """
    Total weight per group, where ``group_of`` maps an asset to its bucket (sector,
    asset class, region). Sums weights that share a bucket.
    """
    exposure: dict[Hashable, float] = {}
    for asset, weight in weights.items():
        group = group_of(asset)
        exposure[group] = exposure.get(group, 0.0) + weight
    return exposure


@dataclass(frozen=True, slots=True)
class ConcentrationSummary:
    herfindahl: float
    effective_holdings: float
    max_weight: float
    top_5_weight: float


def portfolio_concentration(portfolio_data: PortfolioData) -> ConcentrationSummary:
    """Concentration summary from the portfolio's current weights."""
    weights = list(portfolio_data.weights.values())
    return ConcentrationSummary(
        herfindahl=herfindahl_index(weights),
        effective_holdings=effective_holdings(weights),
        max_weight=max_weight(weights),
        top_5_weight=concentration_ratio(weights, 5),
    )


def portfolio_exposure(
    portfolio_data: PortfolioData,
    group_of: Callable[[Asset], Hashable],
) -> dict[Hashable, float]:
    """Exposure of the portfolio bucketed by ``group_of``."""
    return exposure_by_group(portfolio_data.weights, group_of)

