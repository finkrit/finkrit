# finkrit/packages/finkritq/tests/anal/performance/test_flows.py
"""
Time-weighted and money-weighted returns. Hand-built value/flow paths where the
answer is obvious.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from finkritq.anal.performance import money_weighted_return, time_weighted_return
from finkritq.datatype import CashFlow, flows_to_series


class TestTimeWeighted:

    def test_no_flows_is_just_the_compounded_return(self):
        # +10% each of 3 periods -> 1.1^3 - 1 = 0.331.
        values = np.array([100.0, 110.0, 121.0, 133.1])
        assert np.isclose(time_weighted_return(values, np.zeros(4)), 0.331)

    def test_strips_a_contribution(self):
        # A $50 contribution at t2 inflates the value but is not performance,
        # each period is still a true +10%.
        values = np.array([100.0, 110.0, 171.0, 188.1])
        flows = np.array([0.0, 0.0, 50.0, 0.0])
        assert np.isclose(time_weighted_return(values, flows), 0.331)

    def test_annualized(self):
        values = np.array([100.0, 110.0, 121.0, 133.1])
        twr = time_weighted_return(values, np.zeros(4), annualized=True, periods_per_year=3)
        assert np.isclose(twr, 0.331)   # 3 periods, ppy 3 -> already one "year"

    def test_strips_a_withdrawal(self):
        # A $50 withdrawal at t2 shrinks the value but is not a loss. Each period
        # is still a true +10%: t2 grows 110 to 121 then pays out 50, leaving 71.
        values = np.array([100.0, 110.0, 71.0, 78.1])
        flows = np.array([0.0, 0.0, -50.0, 0.0])
        assert np.isclose(time_weighted_return(values, flows), 0.331)

    def test_short_series_is_zero(self):
        assert time_weighted_return(np.array([100.0]), np.array([0.0])) == 0.0


class TestMoneyWeighted:

    def test_no_flows_recovers_the_per_period_rate(self):
        # 100 -> 133.1 over 3 periods with no flows is 10% per period.
        values = np.array([100.0, 110.0, 121.0, 133.1])
        assert np.isclose(money_weighted_return(values, np.zeros(4)), 0.10, atol=1e-6)

    def test_annualized_compounds_the_period_rate(self):
        values = np.array([100.0, 110.0, 121.0, 133.1])
        mwr = money_weighted_return(values, np.zeros(4), annualized=True, periods_per_year=2)
        assert np.isclose(mwr, 1.10 ** 2 - 1.0, atol=1e-6)

    def test_flow_timing_moves_mwr_away_from_twr(self):
        # Same ending value and per-period returns as the TWR flow case, but MWR
        # weights the dollars: a big late contribution earns the last period only.
        values = np.array([100.0, 110.0, 171.0, 188.1])
        flows = np.array([0.0, 0.0, 50.0, 0.0])
        twr = time_weighted_return(values, flows)
        mwr = money_weighted_return(values, flows)
        assert not np.isclose(twr, mwr)

    def test_short_series_is_zero(self):
        assert money_weighted_return(np.array([100.0]), np.array([0.0])) == 0.0

    def test_total_wipeout_has_no_rate(self):
        # An initial outflow that never comes back cannot bracket a root: the NPV
        # is a constant negative for every rate, so the IRR is nan (not a bogus
        # bound). Annualizing must propagate the nan rather than raise or fabricate.
        values = np.array([100.0, 0.0])
        flows = np.zeros(2)
        assert np.isnan(money_weighted_return(values, flows))
        assert np.isnan(money_weighted_return(values, flows, annualized=True))

    def test_withdrawal_timing_moves_mwr_away_from_twr(self):
        # Same per-period returns as the TWR withdrawal case, but pulling money out
        # early means fewer dollars ride the later growth, so MWR diverges from TWR.
        values = np.array([100.0, 110.0, 71.0, 78.1])
        flows = np.array([0.0, 0.0, -50.0, 0.0])
        assert not np.isclose(time_weighted_return(values, flows),
                              money_weighted_return(values, flows))

    def test_long_daily_series_stays_finite(self):
        # Regression: at ~120 periods the IRR bracket used to underflow (1+r)^n to
        # zero, producing inf/nan and returning the bound. A gently rising daily
        # series with a mid contribution must give a small, finite per-period rate.
        n = 121
        values = 22_500.0 * (1.0015 ** np.arange(n))
        flows = np.zeros(n)
        mid = n // 2
        flows[mid] = 20_000.0
        values[mid:] += 20_000.0
        mwr = money_weighted_return(values, flows)
        assert np.isfinite(mwr)
        assert 0.0 < mwr < 0.05          # ~15 bps/day, nowhere near the old bound
        annual = money_weighted_return(values, flows, annualized=True)
        assert np.isfinite(annual)


class TestFlowsToSeries:
    """
    Collapsing dated CashFlows onto a value series' observation dates, the input
    prep that feeds TWR/MWR. Alignment, same-date summing, and sign are what matter.
    """

    dates = np.array(["2026-01-01", "2026-01-02", "2026-01-03"], dtype="datetime64[D]")

    def test_flow_lands_on_its_date(self):
        series = flows_to_series([CashFlow(date(2026, 1, 2), 50.0)], self.dates)
        assert np.array_equal(series, [0.0, 50.0, 0.0])

    def test_same_date_flows_are_summed(self):
        # A contribution and a withdrawal on one day net together in that slot.
        flows = [CashFlow(date(2026, 1, 2), 50.0), CashFlow(date(2026, 1, 2), 25.0)]
        series = flows_to_series(flows, self.dates)
        assert np.isclose(series[1], 75.0)

    def test_withdrawal_keeps_its_sign(self):
        series = flows_to_series([CashFlow(date(2026, 1, 3), -10.0)], self.dates)
        assert np.array_equal(series, [0.0, 0.0, -10.0])

    def test_flow_outside_the_window_is_ignored(self):
        # A flow whose date is not an observation date drops out (no slot to hold
        # it), rather than shifting onto a neighbour or raising.
        series = flows_to_series([CashFlow(date(2026, 6, 1), 999.0)], self.dates)
        assert np.array_equal(series, np.zeros(3))

    def test_no_flows_is_all_zero(self):
        assert np.array_equal(flows_to_series([], self.dates), np.zeros(3))
