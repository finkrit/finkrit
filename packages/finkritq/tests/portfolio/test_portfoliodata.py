# finkritq/tests/portfolio/test_portfoliodata.py
"""
Tests for PortfolioData's derived series, focused on the multi-account
aggregation contract: the same asset held in more than one account must be
summed, not overwritten (regression for the D-A weights bug).
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_account, make_position, make_price_history, make_stock

_FLAT = np.full(10, 100.0)  # flat @ $100 -> market value == quantity * 100


def _two_account_portfolio() -> tuple[Portfolio, object, object]:
    """AAA held in TWO accounts (10 + 90 shares), BBB in one (5 shares)."""
    aaa = make_stock("AAA")
    bbb = make_stock("BBB")

    acct1 = make_account(account_id="a1")
    acct1.positions = [
        make_position(aaa, account=acct1, quantity=Decimal("10"), position_id="p1", lot_id="l1"),
        make_position(bbb, account=acct1, quantity=Decimal("5"), position_id="p2", lot_id="l2"),
    ]
    acct2 = make_account(account_id="a2")
    acct2.positions = [
        make_position(aaa, account=acct2, quantity=Decimal("90"), position_id="p3", lot_id="l3"),
    ]
    portfolio = Portfolio(id="pf", name="Two-account", accounts=[acct1, acct2])
    return portfolio, aaa, bbb


def _portfolio_data() -> PortfolioData:
    portfolio, aaa, bbb = _two_account_portfolio()
    return PortfolioData(
        portfolio=portfolio,
        _histories={aaa: make_price_history(_FLAT), bbb: make_price_history(_FLAT)},
    )


class TestMultiAccountAggregation:

    def test_weights_sum_the_same_asset_across_accounts(self):
        weights = _portfolio_data().weights
        # 100 AAA @100 = 10000, 5 BBB @100 = 500, total 10500
        assert weights[make_stock("AAA")] == 10000.0 / 10500.0
        assert weights[make_stock("BBB")] == 500.0 / 10500.0

    def test_weights_sum_to_one(self):
        assert sum(_portfolio_data().weights.values()) == 1.0

    def test_weight_vector_agrees_with_value(self):
        # weights (was buggy) and value (always summed) must describe the same
        # portfolio: AAA is 100/105 of it.
        data = _portfolio_data()
        aaa_weight = data.weights[make_stock("AAA")]
        # value[0] = 100*100 (AAA) + 5*100 (BBB) = 10500; AAA share = 10000/10500
        assert np.isclose(aaa_weight, 10000.0 / 10500.0)

    def test_weight_vector_length_matches_unique_assets(self):
        data = _portfolio_data()
        assert len(data.weight_vector) == data.n_assets == 2
