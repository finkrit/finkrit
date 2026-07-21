# finkrit/packages/finkritq/tests/anal/risk/test_projection.py
"""
Forward return range: parametric and historical projections. Uses the shared
two_stock_portfolio_data fixture (60 seeded days, real volatility).
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk import forward_return_range
from finkritq.datatype import VaREstimationMethod


class TestParametric:

    def test_low_below_high_and_records_method(self, two_stock_portfolio_data):
        r = forward_return_range(two_stock_portfolio_data)
        assert r.low < r.high
        assert r.method is VaREstimationMethod.PARAMETRIC
        assert np.isfinite(r.low) and np.isfinite(r.high)

    def test_zero_drift_is_symmetric(self, two_stock_portfolio_data):
        # With the drift forced to 0 the parametric band is mu_h +/- z sigma_h
        # centered on 0, so low and high are mirror images.
        r = forward_return_range(two_stock_portfolio_data, expected_return=0.0)
        assert np.isclose(r.low, -r.high)

    def test_higher_confidence_widens_the_downside(self, two_stock_portfolio_data):
        wide = forward_return_range(two_stock_portfolio_data, confidence=0.99, expected_return=0.0)
        narrow = forward_return_range(two_stock_portfolio_data, confidence=0.90, expected_return=0.0)
        assert wide.low < narrow.low

    def test_longer_horizon_widens_the_downside(self, two_stock_portfolio_data):
        far = forward_return_range(two_stock_portfolio_data, horizon_days=252, expected_return=0.0)
        near = forward_return_range(two_stock_portfolio_data, horizon_days=63, expected_return=0.0)
        assert far.low < near.low


class TestHistorical:

    def test_low_below_high_and_records_method(self, two_stock_portfolio_data):
        r = forward_return_range(two_stock_portfolio_data, method=VaREstimationMethod.HISTORICAL)
        assert r.low < r.high
        assert r.method is VaREstimationMethod.HISTORICAL
        assert np.isfinite(r.low) and np.isfinite(r.high)

    def test_monte_carlo_is_rejected(self, two_stock_portfolio_data):
        with pytest.raises(ValueError):
            forward_return_range(two_stock_portfolio_data, method=VaREstimationMethod.MONTE_CARLO)
