# finkrit/packages/finkritq/tests/optimize/test_taxrebalance.py
"""
Tax-budgeted rebalancing. Flat prices (so weights are exact) plus chosen cost
bases so we know exactly which sells are gains vs losses.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np

from finkritq.optimize import tax_aware_rebalance
from finkritq.portfolio import Portfolio, PortfolioData, Position, TaxLot
from finkritq.tests.fixtures import make_price_history, make_stock

_AS_OF = date(2024, 1, 1)
_PRICE = Decimal("90")
_LT = date(2020, 1, 1)   # long-term at the as-of


def _data(specs: dict[str, tuple[str, str]]) -> tuple[PortfolioData, dict]:
    # specs: ticker -> (shares, cost_per_share). Flat price 90 for all.
    stocks = {t: make_stock(t) for t in specs}
    positions = [
        Position(id=f"p-{t}", asset=stocks[t],
                 lots=(TaxLot(id=f"l-{t}", quantity=Decimal(sh), cost_per_share=Decimal(cost), acquired=_LT),))
        for t, (sh, cost) in specs.items()
    ]
    flat = np.full(5, 90.0)
    data = PortfolioData(
        portfolio=Portfolio(id="pf", name="txr", positions=positions),
        _histories={stocks[t]: make_price_history(flat) for t in specs},
    )
    prices = {stocks[t]: _PRICE for t in specs}
    return data, {"stocks": stocks, "prices": prices}


class TestHarvest:

    def test_overweight_loss_position_is_harvested(self):
        # AAA overweight and underwater (cost 130 > price 90): rebalancing sells it
        # at a loss.
        data, ctx = _data({"AAA": ("50", "130"), "BBB": ("50", "90")})
        s = ctx["stocks"]
        plan = tax_aware_rebalance(data, {s["AAA"]: 0.3, s["BBB"]: 0.7}, ctx["prices"], _AS_OF)
        assert len(plan.sells) == 1
        assert plan.sells[0].asset is s["AAA"]
        assert plan.sells[0].is_harvest is True
        assert plan.harvested_loss > 0


class TestGainBudget:

    def _two_gain_book(self):
        # AAA (drift .2) and CCC (drift .1) both cheap-cost -> both gains on a sell.
        data, ctx = _data({"AAA": ("50", "50"), "CCC": ("40", "50"), "BBB": ("10", "90")})
        s = ctx["stocks"]
        target = {s["AAA"]: 0.3, s["BBB"]: 0.4, s["CCC"]: 0.3}
        return data, ctx, target, s

    def test_unlimited_budget_realizes_both_gains(self):
        data, ctx, target, s = self._two_gain_book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF)
        assert {sell.asset for sell in plan.sells} == {s["AAA"], s["CCC"]}
        assert plan.deferred == []
        assert plan.realized_gain > 0

    def test_tight_budget_defers_the_lower_priority_gain(self):
        data, ctx, target, s = self._two_gain_book()
        # AAA sells 20 @ (90-50) = $800 gain, a budget of $800 fits AAA but not
        # AAA+CCC, so CCC (smaller drift) is deferred.
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF, gain_budget=800.0)
        sold = {sell.asset for sell in plan.sells}
        assert s["AAA"] in sold
        assert s["CCC"] in plan.deferred
        assert plan.realized_gain <= Decimal("800")


class TestReplacementSecurity:

    def test_harvest_proceeds_route_to_the_substitute(self):
        data, ctx = _data({"AAA": ("50", "130"), "BBB": ("50", "90")})
        s = ctx["stocks"]
        substitute = make_stock("AAA_ETF")
        plan = tax_aware_rebalance(
            data, {s["AAA"]: 0.3, s["BBB"]: 0.7}, ctx["prices"], _AS_OF,
            replacements={s["AAA"]: substitute},
        )
        assert substitute in plan.replacement_buys
        assert plan.replacement_buys[substitute] > 0
