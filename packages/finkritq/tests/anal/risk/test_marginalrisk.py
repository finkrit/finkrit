# finkrit/tests/risk/test_marginalrisk.py
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.marginalrisk import marginal_contribution_to_risk
from finkritq.anal.risk.volatility import portfolio_volatility
from finkritq.portfolio import PortfolioData
from finkritq.tests.fixtures import make_price_history, make_two_stock_portfolio


class TestMarginalContributionToRisk:

    def test_returns_array_of_correct_length(self, two_stock_portfolio_data):
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)
        assert len(mctr) == two_stock_portfolio_data.n_assets

    def test_returns_ndarray(self, two_stock_portfolio_data):
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)
        assert isinstance(mctr, np.ndarray)

    def test_shape_matches_weights(self, two_stock_portfolio_data):
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)
        assert mctr.shape == two_stock_portfolio_data.weight_vector.shape

    def test_all_values_finite(self, two_stock_portfolio_data):
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)
        assert np.all(np.isfinite(mctr))

    def test_weighted_sum_equals_portfolio_volatility(self, two_stock_portfolio_data):
        """w · MCTR = portfolio volatility (Euler decomposition)."""
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)
        weights = two_stock_portfolio_data.weight_vector
        pvol = portfolio_volatility(two_stock_portfolio_data)
        assert np.dot(weights, mctr) == pytest.approx(pvol, rel=1e-6)

    def test_repeated_calls_identical(self, two_stock_portfolio_data):
        np.testing.assert_allclose(
            marginal_contribution_to_risk(two_stock_portfolio_data),
            marginal_contribution_to_risk(two_stock_portfolio_data))


class TestMarginalContributionToRiskDegenerateData:
    """
    A thin window must fail loud, not return a NaN vector. A NaN MCTR serializes
    to null for every holding and reaches the caller as blank numbers with no
    reason attached, which the agent layer then rationalizes with a wrong story.
    These pin the guards that turn that into a clear error at the source.
    """

    def test_single_observation_rejected_at_portfolio_data(self):
        # One aligned observation cannot even form a return series.
        portfolio, a, b = make_two_stock_portfolio()
        with pytest.raises(ValueError, match="aligned observation"):
            PortfolioData(
                portfolio=portfolio,
                _histories={
                    a: make_price_history([100.0]),
                    b: make_price_history([50.0]),
                },
            )

    def test_nan_close_rejected_at_portfolio_data(self):
        # A gap-filled or bad provider row shows up as a non-finite close.
        portfolio, a, b = make_two_stock_portfolio()
        with pytest.raises(ValueError, match="non-finite close"):
            PortfolioData(
                portfolio=portfolio,
                _histories={
                    a: make_price_history([100.0, float("nan"), 102.0]),
                    b: make_price_history([50.0, 51.0, 52.0]),
                },
            )

    def test_two_observations_rejected_at_covariance(self):
        # Two closes pass PortfolioData (one return exists) but ddof=1 covariance
        # needs at least two returns, so MCTR must raise rather than divide by NaN.
        portfolio, a, b = make_two_stock_portfolio()
        data = PortfolioData(
            portfolio=portfolio,
            _histories={
                a: make_price_history([100.0, 101.0]),
                b: make_price_history([50.0, 50.5]),
            },
        )
        with pytest.raises(ValueError, match="at least 2 return observations"):
            marginal_contribution_to_risk(data)

