# finkrit/packages/finkritq/tests/anal/risk/test_portfolio_beta.py
"""
Tests for portfolio_beta and the benchmark date-alignment it relies on.
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.beta import portfolio_beta
from finkritq.datatype import WeightingBasis
from finkritq.tests.fixtures import make_price_history


def _benchmark_60(seed=11):
    rng = np.random.default_rng(seed)
    closes = np.round(200.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.011, 60))), 4)
    return make_price_history(closes)


class TestPortfolioBeta:

    def test_matches_independent_oracle(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = _benchmark_60()  # 60 dates aligned to the portfolio
        port_returns = np.diff(np.log(pd.value))          # BUY_AND_HOLD realized
        bench_returns = np.diff(np.log(bench.close))
        cov = np.cov(port_returns, bench_returns, ddof=1)
        expected = cov[0, 1] / cov[1, 1]
        assert portfolio_beta(pd, bench, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(expected)

    def test_beta_against_own_value_path_is_one(self, two_stock_portfolio_data):
        # A benchmark whose prices ARE the portfolio's value path has identical
        # returns, so beta must be 1.
        pd = two_stock_portfolio_data
        self_benchmark = make_price_history(pd.value)
        assert portfolio_beta(pd, self_benchmark, basis=WeightingBasis.BUY_AND_HOLD) == pytest.approx(1.0)

    def test_both_bases_finite(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        bench = _benchmark_60()
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_beta(pd, bench, basis=basis))


class TestBenchmarkAlignment:

    def test_missing_date_raises(self, two_stock_portfolio_data):
        # A benchmark on a disjoint calendar cannot be aligned to the portfolio.
        pd = two_stock_portfolio_data
        rng = np.random.default_rng(5)
        closes = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 60))), 4)
        disjoint = make_price_history(closes, start="2030-01-02")
        with pytest.raises(ValueError):
            portfolio_beta(pd, disjoint)

    def test_extra_benchmark_dates_are_ignored(self, two_stock_portfolio_data):
        # A longer benchmark that covers the portfolio's dates still aligns: only
        # the portfolio's observation dates are sampled.
        pd = two_stock_portfolio_data
        rng = np.random.default_rng(7)
        closes = np.round(150.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 90))), 4)
        longer = make_price_history(closes)  # 90 days, superset of the 60
        assert np.isfinite(portfolio_beta(pd, longer))
