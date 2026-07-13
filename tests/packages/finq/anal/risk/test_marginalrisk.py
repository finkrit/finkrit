# finkrit/tests/risk/test_marginalrisk.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.anal.risk.marginalrisk import marginal_contribution_to_risk
from packages.finq.anal.risk.volatility import portfolio_volatility


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
        
