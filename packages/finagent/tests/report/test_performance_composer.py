# finagent/tests/report/test_performance_composer.py
from __future__ import annotations

from datetime import date

from finkritq.datatype import WeightingBasis

from finagent.report.performance import (
    PerformanceMetric,
    PortfolioPerformanceReport,
    compose_portfolio_performance_report,
)
from finagent.tests.fixtures import make_portfolio, make_registry


class TestComposeCore:

    def _report(self, metrics="core"):
        return compose_portfolio_performance_report(make_portfolio(), make_registry(), metrics)

    def test_returns_portfolio_performance_report(self):
        assert isinstance(self._report(), PortfolioPerformanceReport)

    def test_core_fills_core_fields(self):
        r = self._report()
        assert r.total_return is not None
        assert r.annualized_return is not None
        assert r.sharpe_ratio is not None

    def test_core_leaves_non_core_none(self):
        r = self._report()
        assert r.sortino_ratio is None
        assert r.calmar_ratio is None

    def test_portfolio_id_carried(self):
        assert self._report().portfolio_id == "port-1"

    def test_no_errors_on_happy_path(self):
        assert self._report().errors == {}


class TestComposeAll:

    def _report(self):
        return compose_portfolio_performance_report(make_portfolio(), make_registry(), "all")

    def test_all_scalar_metrics_present(self):
        r = self._report()
        for field in ("total_return", "annualized_return", "sharpe_ratio",
                      "sortino_ratio", "calmar_ratio"):
            assert getattr(r, field) is not None, field


class TestComposeSelective:

    def test_only_sharpe(self):
        r = compose_portfolio_performance_report(
            make_portfolio(), make_registry(), {PerformanceMetric.SHARPE_RATIO}
        )
        assert r.sharpe_ratio is not None
        assert r.total_return is None
        assert r.calmar_ratio is None


class TestComposeParameterPassthrough:

    def test_params_recorded(self):
        start, end = date(2023, 1, 1), date(2023, 6, 1)
        r = compose_portfolio_performance_report(
            make_portfolio(), make_registry(), "core",
            basis=WeightingBasis.CONSTANT_MIX, risk_free_rate=0.03, target=0.01,
            periods_per_year=52, start=start, end=end, interval="1wk",
        )
        assert r.params.basis == WeightingBasis.CONSTANT_MIX
        assert r.params.risk_free_rate == 0.03
        assert r.params.target == 0.01
        assert r.params.periods_per_year == 52
        assert r.params.lookback_start == start
        assert r.params.lookback_end == end
        assert r.params.interval == "1wk"

    def test_start_end_interval_threaded_to_history_fetch(self):
        calls: list[tuple[str, object, object, str]] = []
        inner = make_registry()

        class RecordingRegistry:
            def history(self, target, start=None, end=None, interval="1d"):
                calls.append((target.ticker, start, end, interval))
                return inner.history(target, start=start, end=end, interval=interval)

        start, end = date(2023, 1, 1), date(2023, 6, 1)
        compose_portfolio_performance_report(
            make_portfolio(), RecordingRegistry(), {PerformanceMetric.TOTAL_RETURN},
            start=start, end=end, interval="1wk",
        )

        assert calls, "expected at least one history() call"
        for ticker, s, e, i in calls:
            assert (s, e, i) == (start, end, "1wk"), ticker
