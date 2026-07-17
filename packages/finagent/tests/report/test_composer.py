# finagent/tests/report/test_composer.py
from __future__ import annotations

import pytest

from finagent.report.composer import compose_portfolio_risk_report
from finagent.report.metric import ALL, CORE, RiskMetric
from finagent.report.report import DrawdownSummary, PortfolioRiskReport
from finagent.tests.fixtures import make_portfolio, make_registry


class TestComposeCore:

    def _report(self, metrics="core"):
        return compose_portfolio_risk_report(make_portfolio(), make_registry(), metrics)

    def test_returns_portfolio_risk_report(self):
        assert isinstance(self._report(), PortfolioRiskReport)

    def test_core_fills_core_fields(self):
        r = self._report()
        assert r.volatility is not None
        assert r.value_at_risk is not None
        assert r.beta is not None
        assert r.max_drawdown is not None

    def test_core_leaves_non_core_none(self):
        r = self._report()
        assert r.variance is None
        assert r.semivariance is None
        assert r.marginal_contributions is None

    def test_portfolio_id_carried(self):
        assert self._report().portfolio_id == "port-1"

    def test_no_errors_on_happy_path(self):
        assert self._report().errors == {}

    def test_benchmark_recorded_in_params(self):
        assert self._report().params.benchmark_ticker == "^GSPC"


class TestComposeAll:

    def _report(self):
        return compose_portfolio_risk_report(make_portfolio(), make_registry(), "all")

    def test_drawdown_is_summary(self):
        r = self._report()
        assert isinstance(r.drawdown, DrawdownSummary)
        assert r.drawdown.max_drawdown <= 0.0

    def test_contributions_keyed_by_ticker(self):
        r = self._report()
        assert set(r.marginal_contributions) == {"AAA", "BBB"}
        assert set(r.component_contributions) == {"AAA", "BBB"}

    def test_all_scalar_metrics_present(self):
        r = self._report()
        for field in ("volatility", "variance", "semivariance", "downside_deviation",
                      "value_at_risk", "conditional_value_at_risk", "beta", "max_drawdown"):
            assert getattr(r, field) is not None, field


class TestComposeSelective:

    def test_only_drawdown(self):
        r = compose_portfolio_risk_report(make_portfolio(), make_registry(), {RiskMetric.MAX_DRAWDOWN})
        assert r.max_drawdown is not None
        assert r.volatility is None
        assert r.beta is None
        # beta not requested -> no benchmark fetch -> not recorded
        assert r.params.benchmark_ticker is None


class TestComposeResilience:

    def test_benchmark_failure_nulls_beta_not_report(self):
        reg = make_registry()

        class BrokenBenchmark:
            def history(self, target, start=None, end=None, interval="1d"):
                if target.ticker == "^GSPC":
                    raise ValueError("no benchmark data")
                return reg.history(target, start, end, interval)

        r = compose_portfolio_risk_report(
            make_portfolio(), BrokenBenchmark(), {RiskMetric.VOLATILITY, RiskMetric.BETA}
        )
        assert r.volatility is not None       # unaffected
        assert r.beta is None                  # failed gracefully
        assert "beta" in r.errors
        assert r.params.benchmark_ticker is None
