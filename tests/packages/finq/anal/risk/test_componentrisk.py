# finkrit/tests/risk/test_componentrisk.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.anal.risk.componentrisk import component_contribution_to_risk
from packages.finq.anal.risk.volatility import portfolio_volatility


class TestComponentContributionToRisk:

    def test_returns_array_of_correct_length(self, two_stock_portfolio_data):
        cctr = component_contribution_to_risk(two_stock_portfolio_data)
        assert len(cctr) == two_stock_portfolio_data.n_assets

    def test_returns_ndarray(self, two_stock_portfolio_data):
        cctr = component_contribution_to_risk(two_stock_portfolio_data)
        assert isinstance(cctr, np.ndarray)

    def test_shape_matches_weights(self, two_stock_portfolio_data):
        cctr = component_contribution_to_risk(two_stock_portfolio_data)
        assert cctr.shape == two_stock_portfolio_data.weight_vector.shape

    def test_all_values_finite(self, two_stock_portfolio_data):
        cctr = component_contribution_to_risk(two_stock_portfolio_data)
        assert np.all(np.isfinite(cctr))

    def test_sums_to_portfolio_volatility(self, two_stock_portfolio_data):
        """CCTR must sum exactly to portfolio volatility (Euler theorem)."""
        cctr = component_contribution_to_risk(two_stock_portfolio_data)
        pvol = portfolio_volatility(two_stock_portfolio_data)
        assert cctr.sum() == pytest.approx(pvol, rel=1e-6)

    def test_equals_weight_times_marginal(self, two_stock_portfolio_data):
        from packages.finq.anal.risk.marginalrisk import marginal_contribution_to_risk

        weights = two_stock_portfolio_data.weight_vector
        mctr = marginal_contribution_to_risk(two_stock_portfolio_data)

        np.testing.assert_allclose(component_contribution_to_risk(two_stock_portfolio_data), weights * mctr)

    def test_repeated_calls_identical(self, two_stock_portfolio_data):
        np.testing.assert_allclose(component_contribution_to_risk(two_stock_portfolio_data), component_contribution_to_risk(two_stock_portfolio_data))

