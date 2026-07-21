# finkrit/packages/finkritq/tests/anal/performance/test_contribution.py
"""
Contribution to return. The defining property is that the per-holding
contributions sum exactly to the portfolio's total return, checked directly.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from finkritq.anal.performance import contribution_to_return, portfolio_total_return
from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_position, make_price_history, make_stock


def _data():
    a, b, c = make_stock("AAA"), make_stock("BBB"), make_stock("CCC")
    close_a = np.array([100.0, 110.0, 120.0])   # +20%
    close_b = np.array([100.0, 95.0, 90.0])     # -10%
    close_c = np.array([100.0, 100.0, 105.0])   # +5%
    positions = [
        make_position(a, quantity=Decimal("10"), position_id="p-a", lot_id="l-a"),
        make_position(b, quantity=Decimal("10"), position_id="p-b", lot_id="l-b"),
        make_position(c, quantity=Decimal("10"), position_id="p-c", lot_id="l-c"),
    ]
    data = PortfolioData(
        portfolio=Portfolio(id="pf", name="contrib", positions=positions),
        _histories={
            a: make_price_history(close_a),
            b: make_price_history(close_b),
            c: make_price_history(close_c),
        },
    )
    return data, (a, b, c)


class TestContribution:

    def test_sums_to_total_return(self):
        data, _ = _data()
        contributions = contribution_to_return(data)
        assert np.isclose(sum(item.contribution for item in contributions),
                          portfolio_total_return(data))

    def test_ranked_best_first_contributors_and_detractors(self):
        data, (a, b, c) = _data()
        contributions = contribution_to_return(data)
        assert contributions[0].asset is a    # +20% at equal start weight, top
        assert contributions[-1].asset is b   # -10%, the detractor
        values = [item.contribution for item in contributions]
        assert values == sorted(values, reverse=True)

    def test_fields_match_the_definition(self):
        data, (a, b, c) = _data()
        by_asset = {item.asset: item for item in contribution_to_return(data)}
        assert np.isclose(by_asset[a].asset_return, 0.20)
        assert np.isclose(by_asset[a].start_weight, 1.0 / 3.0)
        assert np.isclose(by_asset[a].contribution, 0.20 / 3.0)
