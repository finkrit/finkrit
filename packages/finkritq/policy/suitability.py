# finkrit/packages/finkritq/policy/suitability.py
"""
Suitability: is the portfolio taking the amount of risk comfortability of the account owner.

The most-asked question is not "what is my volatility" but "am I taking
too much risk, the right amount, or not enough, given my tolerance." That is a
comparison, not an absolute: project the portfolio's outcome range over the
owner's horizon and hold it against the comfort band they signed off on.

Downside is strict: if the projected range low is below the owner's floor at
all, that is too much risk. The upside test is optional, only an owner who set a
ceiling can be found to be taking too little. The estimation method (parametric
or historical) is the caller's choice and passes straight through to the forward
range (see anal.risk.forward_return_range).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from finkritq.anal.risk.projection import ForwardRange, forward_return_range
from finkritq.datatype import VaREstimationMethod
from finkritq.policy.policy import RiskTolerance
from finkritq.portfolio import PortfolioData


class SuitabilityVerdict(Enum):
    """Whether the portfolio's risk fits the owner's tolerance band."""

    TOO_MUCH = "too_much"       # projected downside is worse than the owner accepts
    ALIGNED = "aligned"         # the projected range sits within the comfort band
    TOO_LITTLE = "too_little"   # best case falls short of the owner's ceiling (tame)


@dataclass(frozen=True, slots=True)
class Suitability:
    """
    The portfolio's risk standing against an owner's tolerance band.

    Carries the numbers behind the verdict, not just the label: the projected
    floor and ceiling next to the owner's, so the caller can show "your floor
    -8%, projected downside -11%" rather than an opaque call.
    """

    verdict: SuitabilityVerdict
    portfolio_floor: float          # forward range low
    portfolio_ceiling: float        # forward range high
    tolerance_floor: float          # the loss the owner will accept
    tolerance_ceiling: float | None # top of the comfort band, if set
    gap: float                      # portfolio_floor - tolerance_floor (negative => riskier)
    forward_range: ForwardRange


def suitability(
    portfolio_data: PortfolioData,
    tolerance: RiskTolerance,
    method: VaREstimationMethod = VaREstimationMethod.PARAMETRIC,
    expected_return: float | None = None,
) -> Suitability:
    """
    Compare a portfolio's projected range to an owner's comfort band.

    Projects the forward range at the tolerance's own horizon and confidence
    using ``method``. ``gap = portfolio_floor - tolerance_floor``: negative means
    the portfolio can lose more than the owner accepts (TOO_MUCH, strict, any
    exceedance counts). If a ceiling is set and the projected high is below it,
    the portfolio is TOO_LITTLE (tame), otherwise ALIGNED. ``expected_return``
    passes through to the projection (default historical drift, 0.0 for none).
    """
    forward_range = forward_return_range(
        portfolio_data,
        horizon_days=tolerance.horizon_days,
        confidence=tolerance.confidence,
        method=method,
        expected_return=expected_return,
    )
    gap = forward_range.low - tolerance.floor_return

    if forward_range.low < tolerance.floor_return:
        verdict = SuitabilityVerdict.TOO_MUCH
    elif tolerance.ceiling_return is not None and forward_range.high < tolerance.ceiling_return:
        verdict = SuitabilityVerdict.TOO_LITTLE
    else:
        verdict = SuitabilityVerdict.ALIGNED

    return Suitability(
        verdict=verdict,
        portfolio_floor=forward_range.low,
        portfolio_ceiling=forward_range.high,
        tolerance_floor=tolerance.floor_return,
        tolerance_ceiling=tolerance.ceiling_return,
        gap=gap,
        forward_range=forward_range,
    )
