# finkritq/tests/datatype/test_risk_metric.py
"""
RiskMetric, the cross-layer metric vocabulary.

The values are wire format: they appear in tool schemas and serialized
reports, so these tests pin them the way the RestrictionKind incident taught
us to, explicitly, member by member. A rename that feels cosmetic in the enum
is a breaking change everywhere a value was ever written down.
"""
from __future__ import annotations

from finkritq.datatype import PORTFOLIO_ONLY_METRICS, RiskMetric, asset_metrics


class TestValues:

    def test_every_member_carries_an_explicit_stable_value(self):
        expected = {
            "VOLATILITY": "volatility",
            "VARIANCE": "variance",
            "SEMIVARIANCE": "semivariance",
            "DOWNSIDE_DEVIATION": "downside_deviation",
            "VALUE_AT_RISK": "value_at_risk",
            "CONDITIONAL_VALUE_AT_RISK": "conditional_value_at_risk",
            "BETA": "beta",
            "MAX_DRAWDOWN": "max_drawdown",
            "DRAWDOWN": "drawdown",
            "MARGINAL_CONTRIBUTION": "marginal_contribution",
            "COMPONENT_CONTRIBUTION": "component_contribution",
        }
        assert {m.name: m.value for m in RiskMetric} == expected

    def test_no_member_leans_on_auto(self):
        # auto() numbers by definition order, so a reorder silently renumbers
        # everything ever serialized. Strings only.
        assert all(isinstance(m.value, str) for m in RiskMetric)


class TestScope:

    def test_only_the_contribution_metrics_are_portfolio_only(self):
        # They decompose risk across holdings, and one asset has nothing to
        # decompose. Everything else is legal at either scope.
        assert PORTFOLIO_ONLY_METRICS == {
            RiskMetric.MARGINAL_CONTRIBUTION,
            RiskMetric.COMPONENT_CONTRIBUTION,
        }

    def test_asset_metrics_drops_exactly_the_portfolio_only_ones(self):
        kept = asset_metrics(frozenset(RiskMetric))
        assert kept == frozenset(RiskMetric) - PORTFOLIO_ONLY_METRICS

    def test_asset_metrics_leaves_an_asset_legal_set_alone(self):
        selection = frozenset({RiskMetric.BETA, RiskMetric.VOLATILITY})
        assert asset_metrics(selection) == selection
