# finagent/tests/report/test_metric.py
from __future__ import annotations

import pytest

from finagent.report.metric import ALL, CORE, RiskMetric, asset_metrics, resolve_metrics


class TestResolveMetrics:

    def test_core_alias(self):
        assert resolve_metrics("core") == CORE

    def test_all_alias(self):
        assert resolve_metrics("all") == ALL

    def test_case_insensitive(self):
        assert resolve_metrics("CORE") == CORE

    def test_explicit_set_passthrough(self):
        s = {RiskMetric.BETA, RiskMetric.VOLATILITY}
        assert resolve_metrics(s) == frozenset(s)

    def test_unknown_alias_raises(self):
        with pytest.raises(ValueError):
            resolve_metrics("everything")


class TestAssetMetrics:

    def test_drops_portfolio_only_contributions(self):
        stripped = asset_metrics(ALL)
        assert RiskMetric.MARGINAL_CONTRIBUTION not in stripped
        assert RiskMetric.COMPONENT_CONTRIBUTION not in stripped
        assert RiskMetric.VOLATILITY in stripped

    def test_core_has_no_portfolio_only_metrics(self):
        assert asset_metrics(CORE) == CORE
