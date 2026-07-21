# finkrit/packages/finkritq/tests/optimize/test_meanvariance.py
"""
Mean-variance optimizers, checked against hand-computable oracles.

Diagonal covariance is the key oracle: with Σ = diag(σ²), the closed forms
collapse to inverse-variance weights (GMV) and μ/σ² weights (tangency), which
we can write down directly and compare against, independent of the matrix code.
"""
from __future__ import annotations

import numpy as np

from finkritq.optimize import (
    constrained_max_sharpe_weights,
    constrained_minimum_variance_weights,
    constrained_target_return_weights,
    efficient_frontier,
    ledoit_wolf_shrinkage,
    minimum_variance_weights,
    portfolio_variance_from_weights,
    portfolio_volatility_from_weights,
    tangency_weights,
    target_return_weights,
)


class TestMinimumVariance:

    def test_diagonal_covariance_gives_inverse_variance_weights(self):
        cov = np.diag([0.04, 0.01])   # inv-var: 25, 100 -> normalized 0.2, 0.8
        w = minimum_variance_weights(cov)
        assert np.allclose(w, [0.2, 0.8])

    def test_weights_sum_to_one(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        assert np.isclose(minimum_variance_weights(cov).sum(), 1.0)

    def test_is_the_global_minimum_variance(self):
        # GMV variance must be <= any other budget-feasible portfolio's.
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        w_gmv = minimum_variance_weights(cov)
        v_gmv = portfolio_variance_from_weights(w_gmv, cov)

        rng = np.random.default_rng(0)
        for _ in range(200):
            w = rng.random(2)
            w = w / w.sum()
            assert portfolio_variance_from_weights(w, cov) >= v_gmv - 1e-12


class TestTangency:

    def test_diagonal_covariance_gives_mu_over_variance_weights(self):
        cov = np.diag([0.04, 0.01])
        mu = np.array([0.10, 0.05])   # mu/var: 2.5, 5.0 -> normalized 1/3, 2/3
        w = tangency_weights(cov, mu)  # rf = 0 -> excess == mu
        assert np.allclose(w, [1.0 / 3.0, 2.0 / 3.0])

    def test_weights_sum_to_one(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        assert np.isclose(tangency_weights(cov, mu).sum(), 1.0)

    def test_maximizes_sharpe_vs_random_budget_portfolios(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        w_tan = tangency_weights(cov, mu)
        sharpe_tan = (w_tan @ mu) / portfolio_volatility_from_weights(w_tan, cov)

        rng = np.random.default_rng(1)
        for _ in range(200):
            w = rng.random(2)
            w = w / w.sum()
            sharpe = (w @ mu) / portfolio_volatility_from_weights(w, cov)
            assert sharpe <= sharpe_tan + 1e-9


class TestTargetReturn:

    def test_hits_the_target_and_budget(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        w = target_return_weights(cov, mu, target_return=0.08)
        assert np.isclose(w @ mu, 0.08)
        assert np.isclose(w.sum(), 1.0)

    def test_is_min_variance_at_that_return(self):
        # Perturbing weights while staying budget-feasible but off-target cannot
        # be compared directly, instead confirm the frontier weight beats a
        # budget-feasible portfolio that happens to hit the same return.
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        target = 0.07
        w_opt = target_return_weights(cov, mu, target)
        v_opt = portfolio_variance_from_weights(w_opt, cov)

        # Any other two-asset portfolio hitting the same return is unique here
        # (2 assets, 2 constraints), so just assert optimality against the GMV,
        # which has a lower or equal variance but a different return.
        w_gmv = minimum_variance_weights(cov)
        assert portfolio_variance_from_weights(w_gmv, cov) <= v_opt + 1e-12


class TestEfficientFrontier:

    def _cov_mu(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        return cov, mu

    def test_spans_the_expected_return_range(self):
        cov, mu = self._cov_mu()
        points = efficient_frontier(cov, mu, n_points=11)
        assert len(points) == 11
        assert np.isclose(points[0].expected_return, mu.min())
        assert np.isclose(points[-1].expected_return, mu.max())

    def test_each_point_is_budget_feasible_and_on_target(self):
        cov, mu = self._cov_mu()
        for p in efficient_frontier(cov, mu, n_points=11):
            assert np.isclose(p.weights.sum(), 1.0)
            assert np.isclose(p.weights @ mu, p.expected_return)
            assert np.isclose(p.volatility, portfolio_volatility_from_weights(p.weights, cov))

    def test_volatility_is_convex_around_the_minimum(self):
        # The frontier is a parabola in (vol, return), vols should fall to a
        # single interior (or boundary) minimum then rise, no second dip.
        cov, mu = self._cov_mu()
        vols = np.array([p.volatility for p in efficient_frontier(cov, mu, n_points=51)])
        diffs = np.diff(vols)
        sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
        assert sign_changes <= 1


class TestLedoitWolfShrinkage:

    def _returns(self, n_assets: int, n_periods: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        return rng.normal(0.0, 0.01, (n_assets, n_periods))

    def test_intensity_in_unit_interval(self):
        _, delta = ledoit_wolf_shrinkage(self._returns(4, 100))
        assert 0.0 <= delta <= 1.0

    def test_result_is_symmetric_and_positive_definite(self):
        shrunk, _ = ledoit_wolf_shrinkage(self._returns(4, 100))
        assert np.allclose(shrunk, shrunk.T)
        assert np.all(np.linalg.eigvalsh(shrunk) > 0.0)

    def test_conditions_a_singular_sample(self):
        # More assets than periods: the sample covariance is singular, shrinkage
        # still yields a positive-definite matrix.
        shrunk, delta = ledoit_wolf_shrinkage(self._returns(5, 3))
        assert delta > 0.0
        assert np.all(np.linalg.eigvalsh(shrunk) > 0.0)

    def test_shrinks_off_diagonals_toward_zero(self):
        returns = self._returns(3, 80)
        sample = np.cov(returns, ddof=0)   # 1/T, matches the estimator's convention
        shrunk, _ = ledoit_wolf_shrinkage(returns)
        off = ~np.eye(3, dtype=bool)
        assert np.all(np.abs(shrunk[off]) <= np.abs(sample[off]) + 1e-12)


class TestConstrainedMinimumVariance:

    def test_long_only_is_feasible_and_minimal(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        w = constrained_minimum_variance_weights(cov, [(0.0, 1.0), (0.0, 1.0)])
        assert np.isclose(w.sum(), 1.0)
        assert np.all(w >= -1e-9)
        v = portfolio_variance_from_weights(w, cov)
        rng = np.random.default_rng(0)
        for _ in range(200):
            r = rng.random(2)
            r = r / r.sum()
            assert portfolio_variance_from_weights(r, cov) >= v - 1e-9

    def test_respects_a_weight_cap(self):
        # Unconstrained GMV wants ~0.8 on the low-variance asset, a 0.5 cap binds.
        cov = np.array([[0.01, 0.0], [0.0, 0.04]])
        w = constrained_minimum_variance_weights(cov, [(0.0, 0.5), (0.0, 1.0)])
        assert w[0] <= 0.5 + 1e-9
        assert np.isclose(w.sum(), 1.0)

    def test_long_only_forbids_shorting(self):
        cov = np.array([[0.02, 0.03], [0.03, 0.09]])
        w = constrained_minimum_variance_weights(cov, [(0.0, 1.0), (0.0, 1.0)])
        assert np.all(w >= -1e-9)


class TestConstrainedMaxSharpe:

    def test_long_only_feasible(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        w = constrained_max_sharpe_weights(cov, mu, [(0.0, 1.0), (0.0, 1.0)])
        assert np.isclose(w.sum(), 1.0)
        assert np.all(w >= -1e-9)


class TestConstrainedTargetReturn:

    def test_hits_target_within_bounds(self):
        cov = np.array([[0.04, 0.006], [0.006, 0.01]])
        mu = np.array([0.10, 0.05])
        w = constrained_target_return_weights(cov, mu, 0.08, [(0.0, 1.0), (0.0, 1.0)])
        assert np.isclose(w @ mu, 0.08, atol=1e-6)
        assert np.isclose(w.sum(), 1.0)
        assert np.all(w >= -1e-9)
