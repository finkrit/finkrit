# finkrit/packages/finkritq/policy/compliance.py
"""
Measuring a portfolio against its Policy: where has it drifted out of its bands,
and which holding restrictions does it violate.

Supervision to run across a book of portfolios on a
cadence and the breaches are the exceptions to surface.
Everything here reads the portfolio's current weights only, so it needs no return
history, just the composition and the Policy.
"""
from __future__ import annotations

from dataclasses import dataclass

from finkritq.asset import Asset
from finkritq.policy.policy import Policy, Restriction, RestrictionKind
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class DriftBreach:
    """One holding that has drifted past its allowed band."""

    asset: Asset
    current_weight: float
    target_weight: float
    drift: float          # current - target (positive => overweight)
    allowed: float        # the band that was exceeded


@dataclass(frozen=True, slots=True)
class RestrictionViolation:
    """One holding restriction the portfolio breaks right now."""

    restriction: Restriction
    current_weight: float
    detail: str


@dataclass(frozen=True, slots=True)
class PolicyStatus:
    """The full picture of a portfolio's standing against its Policy."""

    in_compliance: bool
    total_drift: float
    drift_breaches: tuple[DriftBreach, ...]
    restriction_violations: tuple[RestrictionViolation, ...]


def drift_breaches(portfolio_data: PortfolioData, policy: Policy) -> list[DriftBreach]:
    """
    Holdings whose distance from their target weight exceeds their band.

    Covers assets in the model, in the portfolio, or both: a model asset that is
    not held drifts from its target toward 0, a held asset absent from the model
    drifts from 0. Returned worst-drift first.
    """
    weights = portfolio_data.weights
    assets = set(weights) | set(policy.target_weights)

    breaches: list[DriftBreach] = []
    for asset in assets:
        current = weights.get(asset, 0.0)
        target = policy.target_weights.get(asset, 0.0)
        drift = current - target
        allowed = policy.band_for(asset).allowed(target)
        if abs(drift) > allowed:
            breaches.append(DriftBreach(asset, current, target, drift, allowed))

    breaches.sort(key=lambda breach: abs(breach.drift), reverse=True)
    return breaches


def restriction_violations(
    portfolio_data: PortfolioData,
    policy: Policy,
) -> list[RestrictionViolation]:
    """
    Holding restrictions the portfolio breaks in its current composition.

    DO_NOT_HOLD, MAX_WEIGHT, and MIN_WEIGHT are all visible in a snapshot.
    DO_NOT_BUY is not: it forbids increasing a position, which only a proposed
    trade can violate, so it is enforced by the rebalance layer rather than here.
    """
    weights = portfolio_data.weights

    violations: list[RestrictionViolation] = []
    for restriction in policy.restrictions:
        weight = weights.get(restriction.asset, 0.0)

        if restriction.kind is RestrictionKind.DO_NOT_HOLD and weight > 0.0:
            violations.append(RestrictionViolation(
                restriction, weight, f"held at {weight:.2%}, must not be held"))
        elif restriction.kind is RestrictionKind.MAX_WEIGHT and weight > restriction.limit:
            violations.append(RestrictionViolation(
                restriction, weight, f"{weight:.2%} exceeds max {restriction.limit:.2%}"))
        elif restriction.kind is RestrictionKind.MIN_WEIGHT and weight < restriction.limit:
            violations.append(RestrictionViolation(
                restriction, weight, f"{weight:.2%} below min {restriction.limit:.2%}"))

    return violations


def policy_status(portfolio_data: PortfolioData, policy: Policy) -> PolicyStatus:
    """
    Combined drift and restriction standing against the Policy.

    ``in_compliance`` is True only when there are no drift breaches and no
    restriction violations. ``total_drift`` is the sum of absolute per-asset
    drifts, a single number for ranking how far out of line the portfolio is.
    """
    breaches = drift_breaches(portfolio_data, policy)
    violations = restriction_violations(portfolio_data, policy)

    weights = portfolio_data.weights
    assets = set(weights) | set(policy.target_weights)
    total_drift = sum(
        abs(weights.get(asset, 0.0) - policy.target_weights.get(asset, 0.0))
        for asset in assets
    )

    return PolicyStatus(
        in_compliance=(not breaches and not violations),
        total_drift=total_drift,
        drift_breaches=tuple(breaches),
        restriction_violations=tuple(violations),
    )
