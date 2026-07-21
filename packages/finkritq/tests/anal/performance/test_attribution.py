# finkrit/packages/finkritq/tests/anal/performance/test_attribution.py
"""
Brinson attribution. The defining property is that the three effects always sum
to the active return, which every test checks, the pure cases isolate one effect.
"""
from __future__ import annotations

import numpy as np

from finkritq.anal.performance import brinson_attribution


class TestBrinson:

    def test_effects_reconcile_to_active_return(self):
        r = brinson_attribution(
            portfolio_weights={"A": 0.6, "B": 0.4},
            benchmark_weights={"A": 0.5, "B": 0.5},
            portfolio_returns={"A": 0.10, "B": 0.05},
            benchmark_returns={"A": 0.08, "B": 0.06},
        )
        assert np.isclose(r.total, r.active_return)
        assert np.isclose(r.allocation, 0.002)
        assert np.isclose(r.selection, 0.005)
        assert np.isclose(r.interaction, 0.003)
        assert np.isclose(r.active_return, 0.01)

    def test_pure_allocation_when_returns_match_benchmark(self):
        # Same returns as the benchmark, only weights differ -> selection and
        # interaction vanish, all active return is allocation.
        r = brinson_attribution(
            portfolio_weights={"A": 0.7, "B": 0.3},
            benchmark_weights={"A": 0.5, "B": 0.5},
            portfolio_returns={"A": 0.10, "B": 0.04},
            benchmark_returns={"A": 0.10, "B": 0.04},
        )
        assert np.isclose(r.selection, 0.0)
        assert np.isclose(r.interaction, 0.0)
        assert np.isclose(r.allocation, r.active_return)

    def test_pure_selection_when_weights_match_benchmark(self):
        # Same weights, only returns differ -> allocation and interaction vanish.
        r = brinson_attribution(
            portfolio_weights={"A": 0.5, "B": 0.5},
            benchmark_weights={"A": 0.5, "B": 0.5},
            portfolio_returns={"A": 0.12, "B": 0.03},
            benchmark_returns={"A": 0.10, "B": 0.04},
        )
        assert np.isclose(r.allocation, 0.0)
        assert np.isclose(r.interaction, 0.0)
        assert np.isclose(r.selection, r.active_return)

    def test_per_segment_effects_sum_to_totals(self):
        r = brinson_attribution(
            {"A": 0.6, "B": 0.4}, {"A": 0.5, "B": 0.5},
            {"A": 0.10, "B": 0.05}, {"A": 0.08, "B": 0.06},
        )
        assert np.isclose(sum(s.allocation for s in r.segments), r.allocation)
        assert np.isclose(sum(s.total for s in r.segments), r.total)

    def test_single_segment_fields_match_the_formula(self):
        # Guard the per-segment numbers themselves, not just their sums. For A:
        # alloc (0.6-0.5)*0.08, selection 0.5*(0.10-0.08), interaction 0.1*0.02.
        r = brinson_attribution(
            {"A": 0.6, "B": 0.4}, {"A": 0.5, "B": 0.5},
            {"A": 0.10, "B": 0.05}, {"A": 0.08, "B": 0.06},
        )
        a = next(s for s in r.segments if s.segment == "A")
        assert np.isclose(a.allocation, 0.008)
        assert np.isclose(a.selection, 0.010)
        assert np.isclose(a.interaction, 0.002)
        assert np.isclose(a.total, 0.020)

    def test_segment_absent_from_benchmark_still_reconciles(self):
        # C is held but not in the benchmark, so its benchmark weight and return
        # default to 0. Missing keys must not break the reconciliation identity,
        # and C's only nonzero effect is interaction (wb is 0, so allocation and
        # selection vanish).
        r = brinson_attribution(
            portfolio_weights={"A": 0.7, "C": 0.3},
            benchmark_weights={"A": 1.0},
            portfolio_returns={"A": 0.05, "C": 0.20},
            benchmark_returns={"A": 0.04},
        )
        assert np.isclose(r.total, r.active_return)
        c = next(s for s in r.segments if s.segment == "C")
        assert np.isclose(c.allocation, 0.0)
        assert np.isclose(c.selection, 0.0)
        assert np.isclose(c.interaction, 0.06)

    def test_negative_active_return_decomposes(self):
        # Underperformance is just a negative active return, the identity holds
        # regardless of sign.
        r = brinson_attribution(
            {"A": 0.5, "B": 0.5}, {"A": 0.5, "B": 0.5},
            {"A": 0.02, "B": 0.01}, {"A": 0.06, "B": 0.05},
        )
        assert r.active_return < 0.0
        assert np.isclose(r.total, r.active_return)

    def test_empty_inputs_are_all_zero(self):
        r = brinson_attribution({}, {}, {}, {})
        assert r.segments == []
        assert np.isclose(r.total, 0.0)
        assert np.isclose(r.active_return, 0.0)
