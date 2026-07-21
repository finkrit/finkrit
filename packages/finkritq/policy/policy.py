# finkrit/packages/finkritq/policy/policy.py
"""
The Policy: the target a portfolio is supervised against.

A portfolio is run toward a target allocation with tolerance bands,
a set of holding restrictions, and an owner's risk tolerance. This module is the
data model for that target. It is pure specification with no notion of who owns
the account or where it custodies, which owner a policy belongs to is a concern
for the layer above finq. Here a Policy is just: target weights, how far they
may drift, what may not be held, and how much loss is acceptable.

The compliance checks that measure a portfolio against a Policy live in
compliance.py, the risk-vs-tolerance comparison in suitability.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from finkritq.asset import Asset


class RestrictionKind(Enum):
    """The kinds of holding restriction a policy can impose on an asset."""

    DO_NOT_HOLD = auto()   # the asset must not be held at all (weight must be 0)
    DO_NOT_BUY = auto()    # existing holding may stay, but no new buying
    MAX_WEIGHT = auto()    # the asset may not exceed a weight cap
    MIN_WEIGHT = auto()    # the asset must be held at least at a weight floor


@dataclass(frozen=True, slots=True)
class Restriction:
    """
    A single holding restriction on one asset.

    ``limit`` is the weight cap or floor for MAX_WEIGHT / MIN_WEIGHT and must be
    omitted for the others. DO_NOT_BUY constrains future trades rather than a
    static snapshot, so it is honored by the rebalance layer, not by the
    snapshot compliance check.
    """

    asset: Asset
    kind: RestrictionKind
    limit: float | None = None

    def __post_init__(self) -> None:
        bounded = self.kind in (RestrictionKind.MAX_WEIGHT, RestrictionKind.MIN_WEIGHT)
        if bounded and self.limit is None:
            raise ValueError(f"{self.kind.name} on {self.asset.ticker} requires a limit.")
        if not bounded and self.limit is not None:
            raise ValueError(f"{self.kind.name} on {self.asset.ticker} does not take a limit.")


@dataclass(frozen=True, slots=True)
class DriftBand:
    """
    How far a holding may drift from its target weight before it is a breach.

    A band can be absolute (percentage points of the whole portfolio), relative
    (a fraction of the target weight), or both. With both set, the allowed
    deviation is the GREATER of the two, the standard convention so that a small
    target weight is not held to an impossibly tight absolute band.
    """

    absolute: float | None = 0.05
    relative: float | None = None

    def __post_init__(self) -> None:
        if self.absolute is None and self.relative is None:
            raise ValueError("A DriftBand needs an absolute or a relative tolerance.")
        for name, value in (("absolute", self.absolute), ("relative", self.relative)):
            if value is not None and value < 0.0:
                raise ValueError(f"DriftBand {name} must be non-negative.")

    def allowed(self, target_weight: float) -> float:
        """The maximum absolute drift permitted for a holding at ``target_weight``."""
        candidates: list[float] = []
        if self.absolute is not None:
            candidates.append(self.absolute)
        if self.relative is not None:
            candidates.append(self.relative * target_weight)
        return max(candidates)


@dataclass(frozen=True, slots=True)
class RiskTolerance:
    """
    The owner's comfort band, expressed as financial quantities.

    ``floor_return`` is the worst return the owner will tolerate over
    ``horizon_days`` at ``confidence`` (e.g. -0.08 means down 8% is the edge of
    comfort), the binding downside. ``ceiling_return`` is the optional top of the
    band: setting it lets the suitability check flag a portfolio that is too
    tame (its best case does not even reach what the owner would accept), left
    None, the check is downside-only. Both are deliberately vendor-neutral: a
    1-to-99 style behavioral score, if wanted, is mapped down to this band in the
    layer above finq.
    """

    floor_return: float
    ceiling_return: float | None = None
    horizon_days: int = 126
    confidence: float = 0.95

    def __post_init__(self) -> None:
        if not 0.0 < self.confidence < 1.0:
            raise ValueError("confidence must be strictly between 0 and 1.")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")
        if self.ceiling_return is not None and self.ceiling_return <= self.floor_return:
            raise ValueError("ceiling_return must be above floor_return.")


@dataclass(frozen=True, slots=True)
class Policy:
    """
    The full target a portfolio is supervised against.

    ``target_weights`` is the model allocation. Each holding is allowed to drift
    within ``default_band`` unless it has an entry in ``band_overrides``.
    ``restrictions`` are holding rules, ``risk_tolerance`` (optional) drives the
    suitability check.
    """

    target_weights: dict[Asset, float]
    default_band: DriftBand = field(default_factory=DriftBand)
    band_overrides: dict[Asset, DriftBand] = field(default_factory=dict)
    restrictions: tuple[Restriction, ...] = ()
    risk_tolerance: RiskTolerance | None = None

    def __post_init__(self) -> None:
        if not self.target_weights:
            raise ValueError("A Policy needs at least one target weight.")
        for asset, weight in self.target_weights.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Target weight for {asset.ticker} must be in [0, 1].")

    def band_for(self, asset: Asset) -> DriftBand:
        """The drift band governing ``asset`` (its override, else the default)."""
        return self.band_overrides.get(asset, self.default_band)
