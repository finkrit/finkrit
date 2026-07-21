# finkrit/packages/finkritq/tests/optimize/test_portfolio_optimizers.py
"""
The PortfolioData entry points: they fetch Σ and μ from the data and return
weights keyed by asset. These are integration tests over synthetic (no-network)
price series, so they check plumbing + invariants, not exact numbers (the exact
math is covered by the array-level oracles in test_meanvariance).
"""
from __future__ import annotations

import numpy as np

from finkritq.optimize import (
    FrontierPoint,
    efficient_frontier_portfolio,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
)
from finkritq.policy import Policy, Restriction, RestrictionKind
from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_position, make_price_history, make_stock


def _portfolio_data() -> PortfolioData:
    # Two distinct, non-collinear series -> invertible covariance.
    rng = np.random.default_rng(7)
    close_a = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.010, 60)))
    close_b = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, 60)))

    stock_a = make_stock("AAA")
    stock_b = make_stock("BBB")
    positions = [
        make_position(stock_a, position_id="p-a", lot_id="l-a"),
        make_position(stock_b, position_id="p-b", lot_id="l-b"),
    ]
    portfolio = Portfolio(id="pf", name="opt", positions=positions)
    return PortfolioData(
        portfolio=portfolio,
        _histories={stock_a: make_price_history(close_a), stock_b: make_price_history(close_b)},
    )


class TestMinimumVariancePortfolio:

    def test_returns_weights_keyed_by_asset_summing_to_one(self):
        data = _portfolio_data()
        weights = minimum_variance_portfolio(data)
        assert set(weights) == set(data.assets)
        assert np.isclose(sum(weights.values()), 1.0)


class TestMaximumSharpePortfolio:

    def test_returns_weights_keyed_by_asset_summing_to_one(self):
        data = _portfolio_data()
        weights = maximum_sharpe_portfolio(data, risk_free_rate=0.02)
        assert set(weights) == set(data.assets)
        assert np.isclose(sum(weights.values()), 1.0)


class TestEfficientFrontierPortfolio:

    def test_returns_frontier_points(self):
        data = _portfolio_data()
        points = efficient_frontier_portfolio(data, n_points=15)
        assert len(points) == 15
        assert all(isinstance(p, FrontierPoint) for p in points)
        for p in points:
            assert np.isclose(p.weights.sum(), 1.0)


class TestPolicyConstrainedOptimizers:

    def test_long_only_default_has_no_negative_weights(self):
        weights = minimum_variance_portfolio(_portfolio_data())
        assert all(w >= -1e-9 for w in weights.values())

    def test_do_not_hold_pins_asset_to_zero(self):
        data = _portfolio_data()
        excluded = data.assets[0]
        policy = Policy(
            target_weights={a: 0.5 for a in data.assets},
            restrictions=(Restriction(excluded, RestrictionKind.DO_NOT_HOLD),),
        )
        weights = minimum_variance_portfolio(data, policy=policy)
        assert np.isclose(weights[excluded], 0.0, atol=1e-9)
        assert np.isclose(sum(weights.values()), 1.0)

    def test_max_weight_caps_the_asset(self):
        data = _portfolio_data()
        capped = data.assets[0]
        policy = Policy(
            target_weights={a: 0.5 for a in data.assets},
            restrictions=(Restriction(capped, RestrictionKind.MAX_WEIGHT, limit=0.3),),
        )
        weights = minimum_variance_portfolio(data, policy=policy)
        assert weights[capped] <= 0.3 + 1e-9

    def test_unconstrained_escape_hatch_still_sums_to_one(self):
        weights = minimum_variance_portfolio(_portfolio_data(), long_only=False, shrinkage=False)
        assert np.isclose(sum(weights.values()), 1.0)
