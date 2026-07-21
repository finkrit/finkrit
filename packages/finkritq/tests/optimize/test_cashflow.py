# finkrit/packages/finkritq/tests/optimize/test_cashflow.py
"""
Cash-flow rebalancing. Flat $100 prices make weights equal to share proportions
and the arithmetic exact: a 60/40 book worth $10,000.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from finkritq.optimize import invest_cashflow
from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_position, make_price_history, make_stock

_FLAT = np.full(5, 100.0)


def _data():
    a, b = make_stock("AAA"), make_stock("BBB")
    pf = Portfolio(id="pf", name="cf", positions=[
        make_position(a, quantity=Decimal("60"), position_id="pa", lot_id="la"),
        make_position(b, quantity=Decimal("40"), position_id="pb", lot_id="lb"),
    ])
    data = PortfolioData(portfolio=pf, _histories={a: make_price_history(_FLAT), b: make_price_history(_FLAT)})
    return data, a, b


class TestDeposit:

    def test_buys_the_underweight_toward_the_model(self):
        data, a, b = _data()
        # New total $12,000, target 50/50 -> $6,000 each. AAA already $6,000, BBB
        # $4,000, so the full $2,000 goes to BBB.
        plan = invest_cashflow(data, {a: 0.5, b: 0.5}, cash=2000.0)
        buys = {t.asset.ticker: t.trade_value for t in plan.trades}
        assert np.isclose(buys["BBB"], 2000.0)
        assert "AAA" not in buys
        assert np.isclose(plan.cash_deployed, 2000.0)
        assert np.isclose(plan.cash_remaining, 0.0)

    def test_set_aside_is_held_back(self):
        data, a, b = _data()
        plan = invest_cashflow(data, {a: 0.5, b: 0.5}, cash=2000.0, set_aside=500.0)
        assert np.isclose(plan.cash_deployed, 1500.0)
        assert np.isclose(plan.cash_remaining, 500.0)
        assert plan.set_aside == 500.0

    def test_all_buys_are_buys(self):
        data, a, b = _data()
        plan = invest_cashflow(data, {a: 0.3, b: 0.7}, cash=5000.0)
        assert all(t.trade_value > 0 for t in plan.trades)


class TestWithdrawal:

    def test_sells_the_overweight_to_raise_cash(self):
        data, a, b = _data()
        # Raise $1,000, new total $9,000, target 50/50 -> $4,500 each. AAA is
        # $6,000 (overweight), BBB $4,000, so the sell comes from AAA.
        plan = invest_cashflow(data, {a: 0.5, b: 0.5}, cash=-1000.0)
        sells = {t.asset.ticker: t.trade_value for t in plan.trades}
        assert np.isclose(sells["AAA"], -1000.0)
        assert np.isclose(plan.cash_deployed, -1000.0)

    def test_raises_the_full_amount(self):
        data, a, b = _data()
        plan = invest_cashflow(data, {a: 0.5, b: 0.5}, cash=-3000.0)
        assert np.isclose(sum(-t.trade_value for t in plan.trades), 3000.0)
