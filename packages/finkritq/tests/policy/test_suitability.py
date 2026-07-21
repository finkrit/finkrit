# finkrit/packages/finkritq/tests/policy/test_suitability.py
"""
Suitability: compare a portfolio's projected range to an owner's comfort band.
Verdicts are driven by where the projected floor sits relative to the tolerance.
"""
from __future__ import annotations

import numpy as np

from finkritq.datatype import VaREstimationMethod
from finkritq.policy import RiskTolerance, SuitabilityVerdict, suitability


class TestSuitability:

    def test_too_much_when_floor_is_zero(self, varying_portfolio):
        # An owner who will not accept any loss: the 6-month downside is negative,
        # so the portfolio is taking too much risk, and the gap is negative.
        tolerance = RiskTolerance(floor_return=0.0)
        result = suitability(varying_portfolio, tolerance)
        assert result.verdict is SuitabilityVerdict.TOO_MUCH
        assert result.gap < 0.0

    def test_aligned_when_floor_deep_and_no_ceiling(self, varying_portfolio):
        # A very tolerant owner with no ceiling: downside clears the floor and
        # there is no upside test, so aligned.
        tolerance = RiskTolerance(floor_return=-0.90)
        result = suitability(varying_portfolio, tolerance)
        assert result.verdict is SuitabilityVerdict.ALIGNED
        assert result.gap > 0.0

    def test_too_little_when_ceiling_out_of_reach(self, varying_portfolio):
        # Downside is fine, but the best case cannot reach the owner's ceiling,
        # so the portfolio is tamer than they would accept.
        tolerance = RiskTolerance(floor_return=-0.90, ceiling_return=0.90)
        result = suitability(varying_portfolio, tolerance)
        assert result.verdict is SuitabilityVerdict.TOO_LITTLE

    def test_result_echoes_both_bands(self, varying_portfolio):
        tolerance = RiskTolerance(floor_return=-0.10, ceiling_return=0.20)
        result = suitability(varying_portfolio, tolerance)
        assert result.tolerance_floor == -0.10
        assert result.tolerance_ceiling == 0.20
        assert result.portfolio_floor == result.forward_range.low
        assert result.portfolio_ceiling == result.forward_range.high

    def test_method_passes_through_to_the_projection(self, varying_portfolio):
        tolerance = RiskTolerance(floor_return=-0.20)
        result = suitability(varying_portfolio, tolerance,
                             method=VaREstimationMethod.HISTORICAL)
        assert result.forward_range.method is VaREstimationMethod.HISTORICAL
        assert np.isfinite(result.portfolio_floor)
