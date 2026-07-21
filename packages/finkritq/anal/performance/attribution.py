# finkrit/packages/finkritq/anal/performance/attribution.py
"""
Brinson performance attribution (aka "return decomposition"), splitting a
portfolio's active return (portfolio minus benchmark) into the decisions that
produced it.

The classic Brinson-Hood-Beebower decomposition, per segment i (an asset, sector,
or asset class):

  allocation_i  = (w_p_i - w_b_i) * R_b_i           (over/underweighting segments)
  selection_i   =  w_b_i * (R_p_i - R_b_i)          (picking within a segment)
  interaction_i = (w_p_i - w_b_i) * (R_p_i - R_b_i) (the cross term)

Summed across segments these equal the total active return R_p - R_b exactly, so
the attribution always reconciles. Weights and segment returns are the inputs.
Where the segments come from (assets, GICS sectors, asset classes) is the caller's
choice.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable


@dataclass(frozen=True, slots=True)
class SegmentAttribution:
    segment: Hashable
    allocation: float
    selection: float
    interaction: float

    @property
    def total(self) -> float:
        return self.allocation + self.selection + self.interaction


@dataclass(frozen=True, slots=True)
class AttributionResult:
    segments: list[SegmentAttribution]
    allocation: float
    selection: float
    interaction: float
    active_return: float          # portfolio return - benchmark return

    @property
    def total(self) -> float:
        return self.allocation + self.selection + self.interaction


def brinson_attribution(
    portfolio_weights: dict[Hashable, float],
    benchmark_weights: dict[Hashable, float],
    portfolio_returns: dict[Hashable, float],
    benchmark_returns: dict[Hashable, float],
) -> AttributionResult:
    """
    Decompose active return into allocation, selection, and interaction by segment.

    All four dicts are keyed by segment. A segment missing from a dict contributes
    0 for that term. The per-segment effects sum to the total active return, so
    ``result.total`` equals ``result.active_return`` up to floating point.
    """
    segments = (
        set(portfolio_weights) | set(benchmark_weights)
        | set(portfolio_returns) | set(benchmark_returns)
    )

    per_segment: list[SegmentAttribution] = []
    total_alloc = total_sel = total_inter = 0.0
    portfolio_return = 0.0
    benchmark_return = 0.0

    for segment in segments:
        wp = portfolio_weights.get(segment, 0.0)
        wb = benchmark_weights.get(segment, 0.0)
        rp = portfolio_returns.get(segment, 0.0)
        rb = benchmark_returns.get(segment, 0.0)

        allocation = (wp - wb) * rb
        selection = wb * (rp - rb)
        interaction = (wp - wb) * (rp - rb)

        per_segment.append(SegmentAttribution(segment, allocation, selection, interaction))
        total_alloc += allocation
        total_sel += selection
        total_inter += interaction
        portfolio_return += wp * rp
        benchmark_return += wb * rb

    return AttributionResult(
        segments=per_segment,
        allocation=total_alloc,
        selection=total_sel,
        interaction=total_inter,
        active_return=portfolio_return - benchmark_return,
    )


