# finkrit/packages/finkritq/tests/optimize/test_taxrebalance.py
"""
Tax-budgeted rebalancing. Flat prices (so weights are exact) plus chosen cost
bases so we know exactly which sells are gains vs losses.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np

from finkritq.optimize import tax_aware_rebalance, tax_aware_rebalance_to_policy
from finkritq.policy import Policy, Restriction, RestrictionKind
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


class TestTaxAwareRebalanceToPolicy:

    def test_on_model_policy_has_no_sells(self):
        data, ctx = _data({"AAA": ("50", "50"), "BBB": ("50", "50")})
        s = ctx["stocks"]
        policy = Policy(target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5})
        plan = tax_aware_rebalance_to_policy(data, policy, ctx["prices"], _AS_OF)
        assert plan.sells == []
        assert plan.deferred == []

    def test_restriction_forces_a_sell_the_target_would_not(self):
        # AAA is on target (0.5) so a bare rebalance leaves it, but DO_NOT_HOLD
        # forces it out, and being underwater it is realized as a harvest.
        data, ctx = _data({"AAA": ("50", "130"), "BBB": ("50", "90")})
        s = ctx["stocks"]
        policy = Policy(
            target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5},
            restrictions=(Restriction(s["AAA"], RestrictionKind.DO_NOT_HOLD),),
        )
        plan = tax_aware_rebalance_to_policy(data, policy, ctx["prices"], _AS_OF)
        assert {sell.asset for sell in plan.sells} == {s["AAA"]}
        assert plan.sells[0].is_harvest is True

    def test_policy_path_respects_the_gain_budget(self):
        # AAA (drift .2) and CCC (drift .1) are both gains, an $800 budget fits AAA
        # but not both, so CCC defers, same budgeting the model path does.
        data, ctx = _data({"AAA": ("50", "50"), "CCC": ("40", "50"), "BBB": ("10", "90")})
        s = ctx["stocks"]
        policy = Policy(target_weights={s["AAA"]: 0.3, s["BBB"]: 0.4, s["CCC"]: 0.3})
        plan = tax_aware_rebalance_to_policy(data, policy, ctx["prices"], _AS_OF, gain_budget=800.0)
        sold = {sell.asset for sell in plan.sells}
        assert s["AAA"] in sold
        assert s["CCC"] in plan.deferred


class TestPartialFill:
    """The two-gain book: AAA drift .2 (sell $1,800 = 20 sh, gain $800) and CCC
    drift .1 (sell $900 = 10 sh, gain $400), total value $9,000, all gains at
    $40/share. Budgets are chosen to land inside those figures."""

    def _book(self):
        data, ctx = _data({"AAA": ("50", "50"), "CCC": ("40", "50"), "BBB": ("10", "90")})
        s = ctx["stocks"]
        target = {s["AAA"]: 0.3, s["BBB"]: 0.4, s["CCC"]: 0.3}
        return data, ctx, target, s

    def test_partial_fill_exhausts_the_budget_exactly(self):
        # Budget 1,000: AAA takes 800, CCC's 400 does not fit whole, so it
        # fills 200/40 = 5 of its 10 requested shares and the budget lands on
        # exactly zero remaining.
        data, ctx, target, s = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF,
                                   gain_budget=1000.0, partial_fill=True)
        assert plan.realized_gain == Decimal("1000")
        assert plan.deferred == []
        by_ticker = {sell.asset.ticker: sell for sell in plan.sells}
        assert by_ticker["AAA"].is_partial is False
        assert by_ticker["CCC"].is_partial is True
        assert by_ticker["CCC"].sale.quantity_sold == Decimal("5")

    def test_partial_fill_still_defers_when_not_one_share_fits(self):
        # Budget 800: AAA consumes it to the dollar, CCC faces zero room
        # against a pure gain lot, so it defers whole rather than partially.
        data, ctx, target, s = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF,
                                   gain_budget=800.0, partial_fill=True)
        assert plan.realized_gain == Decimal("800")
        assert plan.deferred == [s["CCC"]]
        assert all(not sell.is_partial for sell in plan.sells)

    def test_partial_fill_off_is_the_old_behavior(self):
        data, ctx, target, s = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF, gain_budget=1000.0)
        assert plan.realized_gain == Decimal("800")
        assert plan.deferred == [s["CCC"]]


class TestResidualDrift:

    def _book(self):
        data, ctx = _data({"AAA": ("50", "50"), "CCC": ("40", "50"), "BBB": ("10", "90")})
        s = ctx["stocks"]
        target = {s["AAA"]: 0.3, s["BBB"]: 0.4, s["CCC"]: 0.3}
        return data, ctx, target, s

    def test_full_rebalance_leaves_no_residual(self):
        data, ctx, target, _ = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF)
        assert abs(plan.residual_drift) < 1e-9

    def test_a_deferral_leaves_its_whole_drift(self):
        # CCC deferred means its .1 of overweight is still held.
        data, ctx, target, _ = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF, gain_budget=800.0)
        assert abs(plan.residual_drift - 0.1) < 1e-9

    def test_band_edge_leaves_the_tolerance_on_every_traded_name(self):
        # Both names trade to the edge of a .05 band, leaving .05 each.
        from finkritq.datatype import RebalanceSizing
        data, ctx, target, _ = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF,
                                   tolerance=0.05, sizing=RebalanceSizing.TO_BAND_EDGE)
        assert abs(plan.residual_drift - 0.1) < 1e-9

    def test_a_partial_fill_leaves_the_unexecuted_remainder(self):
        # CCC fills 5 of 10 shares, so half its .1 drift remains.
        data, ctx, target, _ = self._book()
        plan = tax_aware_rebalance(data, target, ctx["prices"], _AS_OF,
                                   gain_budget=1000.0, partial_fill=True)
        assert abs(plan.residual_drift - 0.05) < 1e-9


class TestCompareStrategies:

    def _run(self, gain_budget=1000.0, tolerance=0.05):
        from finkritq.optimize import compare_rebalance_strategies
        data, ctx = _data({"AAA": ("50", "50"), "CCC": ("40", "50"), "BBB": ("10", "90")})
        s = ctx["stocks"]
        target = {s["AAA"]: 0.3, s["BBB"]: 0.4, s["CCC"]: 0.3}
        return compare_rebalance_strategies(
            data, target, ctx["prices"], _AS_OF,
            gain_budget=gain_budget, tolerance=tolerance,
        )

    def test_returns_every_named_strategy(self):
        from finkritq.optimize import REBALANCE_STRATEGIES
        plans = self._run()
        assert set(plans) == set(REBALANCE_STRATEGIES)

    def test_the_rows_tell_the_tradeoff_story(self):
        # Same target, prices, and $1,000 budget across all three rows:
        #   full:         AAA's 800 fits, CCC's 400 does not -> deferred.
        #   band_edge:    smaller sells (600 + 200) all fit, tolerance remains.
        #   partial_fill: AAA whole, CCC half, budget exhausted to the dollar.
        plans = self._run()
        assert plans["full"].realized_gain == Decimal("800")
        assert abs(plans["full"].residual_drift - 0.1) < 1e-9
        # Band edge dollar sizing runs through float scale factors, so the
        # realized figure carries float noise where full/partial are exact.
        assert abs(float(plans["band_edge"].realized_gain) - 800.0) < 1e-6
        assert abs(plans["band_edge"].residual_drift - 0.1) < 1e-9
        assert plans["partial_fill"].realized_gain == Decimal("1000")
        assert abs(plans["partial_fill"].residual_drift - 0.05) < 1e-9

    def test_rejects_a_zero_tolerance(self):
        import pytest
        with pytest.raises(ValueError, match="positive tolerance"):
            self._run(tolerance=0.0)
