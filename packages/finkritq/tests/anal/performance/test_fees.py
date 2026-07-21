# finkrit/packages/finkritq/tests/anal/performance/test_fees.py
"""
Gross-to-net return. A flat annual fee applied as a value haircut.
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.performance import net_of_fees


class TestNetOfFees:

    def test_zero_fee_leaves_gross_unchanged(self):
        assert np.isclose(net_of_fees(0.10, 0.0), 0.10)

    def test_fee_reduces_the_return(self):
        # One year: net = (1 + gross)(1 - fee) - 1.
        assert np.isclose(net_of_fees(0.10, 0.01), 1.10 * 0.99 - 1.0)
        assert net_of_fees(0.10, 0.01) < 0.10

    def test_fee_compounds_over_multiple_years(self):
        one_year = net_of_fees(0.0, 0.01, years=1.0)
        two_years = net_of_fees(0.0, 0.01, years=2.0)
        assert np.isclose(one_year, -0.01)
        assert np.isclose(two_years, 0.99 ** 2 - 1.0)
        assert two_years < one_year

    def test_rejects_out_of_range_fee(self):
        with pytest.raises(ValueError):
            net_of_fees(0.10, 1.0)
        with pytest.raises(ValueError):
            net_of_fees(0.10, -0.01)
