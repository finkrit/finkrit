# finkrit/packages/finkritq/tests/optimize/test_expected_returns.py
from __future__ import annotations

import numpy as np

from finkritq.optimize import expected_returns_from_returns


class TestExpectedReturnsFromReturns:

    def test_arithmetic_mean_per_asset(self):
        returns = np.array([
            [0.01, 0.02, 0.03],   # mean 0.02
            [0.00, 0.00, 0.00],   # mean 0.00
        ])
        mu = expected_returns_from_returns(returns, annualized=False)
        assert np.allclose(mu, [0.02, 0.0])

    def test_annualization_scales_by_periods_per_year(self):
        returns = np.array([[0.01, 0.02, 0.03]])
        mu = expected_returns_from_returns(returns, annualized=True, periods_per_year=252)
        assert np.allclose(mu, [0.02 * 252])

    def test_shape_matches_asset_count(self):
        returns = np.zeros((5, 30))
        assert expected_returns_from_returns(returns).shape == (5,)
