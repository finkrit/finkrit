# finkrit/packages/finkritq/tests/policy/test_compliance.py
"""
Compliance: drift breaches and restriction violations of a portfolio against its
policy. The weighted_portfolio fixture is exactly 50/30/20 (AAA/BBB/CCC).
"""
from __future__ import annotations

import numpy as np

from finkritq.policy import (
    DriftBand,
    Policy,
    Restriction,
    RestrictionKind,
    drift_breaches,
    policy_status,
    restriction_violations,
)


class TestDriftBreaches:

    def test_only_out_of_band_holdings_breach(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        # Target a third each, default 5% band. AAA (50% vs 33%) and CCC (20% vs
        # 33%) breach, BBB (30% vs 33%) is within band.
        policy = Policy(target_weights={a: 1 / 3, b: 1 / 3, c: 1 / 3})
        breaches = drift_breaches(data, policy)
        assert [breach.asset for breach in breaches] == [a, c]   # worst drift first

    def test_wide_override_suppresses_a_breach(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        policy = Policy(
            target_weights={a: 1 / 3, b: 1 / 3, c: 1 / 3},
            band_overrides={a: DriftBand(absolute=0.25)},
        )
        assert a not in [breach.asset for breach in drift_breaches(data, policy)]

    def test_on_model_portfolio_has_no_breaches(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        policy = Policy(target_weights={a: 0.5, b: 0.3, c: 0.2})
        assert drift_breaches(data, policy) == []


class TestRestrictionViolations:

    def test_do_not_hold_flags_a_held_asset(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        policy = Policy(
            target_weights={a: 0.5, b: 0.3, c: 0.2},
            restrictions=(Restriction(a, RestrictionKind.DO_NOT_HOLD),),
        )
        violations = restriction_violations(data, policy)
        assert len(violations) == 1
        assert violations[0].restriction.asset is a

    def test_max_weight_and_min_weight(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        policy = Policy(
            target_weights={a: 0.5, b: 0.3, c: 0.2},
            restrictions=(
                Restriction(a, RestrictionKind.MAX_WEIGHT, limit=0.4),   # 50% > 40%
                Restriction(c, RestrictionKind.MIN_WEIGHT, limit=0.3),   # 20% < 30%
            ),
        )
        assert len(restriction_violations(data, policy)) == 2

    def test_satisfied_restrictions_do_not_flag(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        policy = Policy(
            target_weights={a: 0.5, b: 0.3, c: 0.2},
            restrictions=(Restriction(a, RestrictionKind.MAX_WEIGHT, limit=0.6),),
        )
        assert restriction_violations(data, policy) == []


class TestPolicyStatus:

    def test_in_compliance_when_on_model_and_unrestricted(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        status = policy_status(data, Policy(target_weights={a: 0.5, b: 0.3, c: 0.2}))
        assert status.in_compliance is True
        assert np.isclose(status.total_drift, 0.0)

    def test_out_of_compliance_reports_total_drift(self, weighted_portfolio):
        data, (a, b, c) = weighted_portfolio
        status = policy_status(data, Policy(target_weights={a: 1 / 3, b: 1 / 3, c: 1 / 3}))
        assert status.in_compliance is False
        # |0.5-1/3| + |0.3-1/3| + |0.2-1/3|
        assert np.isclose(status.total_drift, 1 / 3)
