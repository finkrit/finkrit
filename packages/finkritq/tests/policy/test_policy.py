# finkrit/packages/finkritq/tests/policy/test_policy.py
"""
The policy data model: band arithmetic and the dataclass validation that keeps a
policy well-formed.
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.policy import (
    DriftBand,
    Policy,
    Restriction,
    RestrictionKind,
    RiskTolerance,
)
from finkritq.tests.fixtures import make_stock


class TestDriftBand:

    def test_absolute_only_ignores_target(self):
        band = DriftBand(absolute=0.05)
        assert band.allowed(0.10) == 0.05
        assert band.allowed(0.90) == 0.05

    def test_relative_only_scales_with_target(self):
        band = DriftBand(absolute=None, relative=0.20)
        assert np.isclose(band.allowed(0.50), 0.10)
        assert np.isclose(band.allowed(0.10), 0.02)

    def test_both_takes_the_greater(self):
        # Greater-of convention: a small target keeps the absolute floor, a large
        # target lets the relative band open up.
        band = DriftBand(absolute=0.05, relative=0.20)
        assert np.isclose(band.allowed(0.10), 0.05)   # relative 0.02 < absolute 0.05
        assert np.isclose(band.allowed(0.50), 0.10)   # relative 0.10 > absolute 0.05

    def test_empty_band_rejected(self):
        with pytest.raises(ValueError):
            DriftBand(absolute=None, relative=None)

    def test_negative_band_rejected(self):
        with pytest.raises(ValueError):
            DriftBand(absolute=-0.01)


class TestRestriction:

    def test_bounded_kind_requires_limit(self):
        with pytest.raises(ValueError):
            Restriction(make_stock("AAA"), RestrictionKind.MAX_WEIGHT)

    def test_unbounded_kind_rejects_limit(self):
        with pytest.raises(ValueError):
            Restriction(make_stock("AAA"), RestrictionKind.DO_NOT_HOLD, limit=0.1)

    def test_valid_restrictions_build(self):
        assert Restriction(make_stock("AAA"), RestrictionKind.DO_NOT_HOLD)
        assert Restriction(make_stock("AAA"), RestrictionKind.MAX_WEIGHT, limit=0.3)


class TestRiskTolerance:

    def test_ceiling_must_exceed_floor(self):
        with pytest.raises(ValueError):
            RiskTolerance(floor_return=-0.05, ceiling_return=-0.10)

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            RiskTolerance(floor_return=-0.05, confidence=1.0)

    def test_positive_horizon(self):
        with pytest.raises(ValueError):
            RiskTolerance(floor_return=-0.05, horizon_days=0)

    def test_floor_only_is_valid(self):
        assert RiskTolerance(floor_return=-0.08).ceiling_return is None


class TestPolicy:

    def test_empty_target_rejected(self):
        with pytest.raises(ValueError):
            Policy(target_weights={})

    def test_weight_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            Policy(target_weights={make_stock("AAA"): 1.5})

    def test_band_for_uses_override_then_default(self):
        a, b = make_stock("AAA"), make_stock("BBB")
        override = DriftBand(absolute=0.20)
        policy = Policy(target_weights={a: 0.5, b: 0.5}, band_overrides={a: override})
        assert policy.band_for(a) is override
        assert policy.band_for(b) is policy.default_band
