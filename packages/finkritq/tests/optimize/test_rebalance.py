# finkrit/packages/finkritq/tests/optimize/test_rebalance.py
"""
Rebalance-to-model. Flat $100 prices make market-value weights equal to share
proportions, so every expected trade is hand-computable.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from finkritq.optimize import rebalance_to_model, rebalance_to_policy, total_drift
from finkritq.policy import DriftBand, Policy, Restriction, RestrictionKind
from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_position, make_price_history, make_stock

_FLAT = np.full(5, 100.0)  # value == quantity * 100


def _data(quantities: dict[str, str]) -> tuple[PortfolioData, dict[str, object]]:
    stocks = {t: make_stock(t) for t in quantities}
    positions = [
        make_position(stocks[t], quantity=Decimal(q), position_id=f"p-{t}", lot_id=f"l-{t}")
        for t, q in quantities.items()
    ]
    portfolio = Portfolio(id="pf", name="rebalance", positions=positions)
    data = PortfolioData(
        portfolio=portfolio,
        _histories={stocks[t]: make_price_history(_FLAT) for t in quantities},
    )
    return data, stocks


class TestRebalanceToModel:

    def test_full_rebalance_computes_dollar_trades(self):
        # 60 AAA + 40 BBB @ $100 -> weights 0.6/0.4, total value $10,000.
        data, s = _data({"AAA": "60", "BBB": "40"})
        target = {s["AAA"]: 0.5, s["BBB"]: 0.5}

        trades = {t.asset.ticker: t for t in rebalance_to_model(data, target)}
        assert np.isclose(trades["AAA"].trade_value, -1000.0)  # sell $1,000
        assert np.isclose(trades["BBB"].trade_value, +1000.0)  # buy  $1,000
        assert trades["AAA"].is_buy is False
        assert trades["BBB"].is_buy is True

    def test_tolerance_band_skips_small_drift(self):
        data, s = _data({"AAA": "60", "BBB": "40"})
        target = {s["AAA"]: 0.5, s["BBB"]: 0.5}  # drift 0.10 each
        assert rebalance_to_model(data, target, tolerance=0.15) == []

    def test_asset_in_model_not_held_is_a_buy(self):
        data, s = _data({"AAA": "100"})           # 100% AAA
        ccc = make_stock("CCC")
        target = {s["AAA"]: 0.5, ccc: 0.5}
        trades = {t.asset.ticker: t for t in rebalance_to_model(data, target)}
        assert np.isclose(trades["CCC"].trade_value, +5000.0)  # buy into new name
        assert trades["CCC"].current_weight == 0.0

    def test_asset_held_not_in_model_is_full_sell(self):
        data, s = _data({"AAA": "50", "BBB": "50"})
        target = {s["AAA"]: 1.0}                    # BBB dropped from model
        trades = {t.asset.ticker: t for t in rebalance_to_model(data, target)}
        assert trades["BBB"].target_weight == 0.0
        assert np.isclose(trades["BBB"].trade_value, -5000.0)  # sell all BBB

    def test_sorted_by_drift_severity(self):
        data, s = _data({"AAA": "70", "BBB": "20", "CCC": "10"})
        target = {s["AAA"]: 0.4, s["BBB"]: 0.3, s["CCC"]: 0.3}
        trades = rebalance_to_model(data, target)
        drifts = [abs(t.drift) for t in trades]
        assert drifts == sorted(drifts, reverse=True)


class TestTotalDrift:

    def test_sums_absolute_drift(self):
        data, s = _data({"AAA": "60", "BBB": "40"})
        target = {s["AAA"]: 0.5, s["BBB"]: 0.5}
        assert np.isclose(total_drift(data, target), 0.2)  # 0.1 + 0.1

    def test_zero_when_on_model(self):
        data, s = _data({"AAA": "50", "BBB": "50"})
        target = {s["AAA"]: 0.5, s["BBB"]: 0.5}
        assert np.isclose(total_drift(data, target), 0.0)


class TestRebalanceToPolicy:

    def test_on_model_no_restrictions_no_trades(self):
        data, s = _data({"AAA": "50", "BBB": "50"})
        policy = Policy(target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5})
        assert rebalance_to_policy(data, policy) == []

    def test_band_breach_trades_with_drift_reason(self):
        # 0.6/0.4 vs a 0.5/0.5 model, default 5% band -> both breach.
        data, s = _data({"AAA": "60", "BBB": "40"})
        policy = Policy(target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5})
        trades = {t.asset.ticker: t for t in rebalance_to_policy(data, policy)}
        assert trades["AAA"].reason == "drift"
        assert np.isclose(trades["AAA"].trade_value, -1000.0)

    def test_within_band_no_trade(self):
        data, s = _data({"AAA": "60", "BBB": "40"})   # drift 0.10 each
        policy = Policy(target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5},
                        default_band=DriftBand(absolute=0.15))
        assert rebalance_to_policy(data, policy) == []

    def test_do_not_hold_forces_full_sell(self):
        # BBB is on target, but DO_NOT_HOLD forces it out anyway.
        data, s = _data({"AAA": "50", "BBB": "50"})
        policy = Policy(
            target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5},
            restrictions=(Restriction(s["BBB"], RestrictionKind.DO_NOT_HOLD),),
        )
        trades = {t.asset.ticker: t for t in rebalance_to_policy(data, policy)}
        assert trades["BBB"].reason == "do_not_hold"
        assert np.isclose(trades["BBB"].trade_value, -5000.0)
        assert "AAA" not in trades   # on target, left alone

    def test_max_weight_sells_down_to_cap(self):
        data, s = _data({"AAA": "60", "BBB": "40"})
        policy = Policy(
            target_weights={s["AAA"]: 0.6, s["BBB"]: 0.4},   # on model
            restrictions=(Restriction(s["AAA"], RestrictionKind.MAX_WEIGHT, limit=0.5),),
        )
        trades = {t.asset.ticker: t for t in rebalance_to_policy(data, policy)}
        assert trades["AAA"].reason == "max_weight"
        assert np.isclose(trades["AAA"].trade_value, -1000.0)   # 0.6 -> 0.5

    def test_min_weight_buys_up_to_floor(self):
        data, s = _data({"AAA": "50", "BBB": "50"})
        policy = Policy(
            target_weights={s["AAA"]: 0.5, s["BBB"]: 0.5},
            restrictions=(Restriction(s["BBB"], RestrictionKind.MIN_WEIGHT, limit=0.6),),
        )
        trades = {t.asset.ticker: t for t in rebalance_to_policy(data, policy)}
        assert trades["BBB"].reason == "min_weight"
        assert np.isclose(trades["BBB"].trade_value, +1000.0)   # 0.5 -> 0.6

    def test_do_not_buy_suppresses_the_buy(self):
        # AAA is underweight (would buy) but DO_NOT_BUY: leave it, still sell BBB.
        data, s = _data({"AAA": "40", "BBB": "60"})
        policy = Policy(
            target_weights={s["AAA"]: 0.6, s["BBB"]: 0.4},
            restrictions=(Restriction(s["AAA"], RestrictionKind.DO_NOT_BUY),),
        )
        trades = {t.asset.ticker: t for t in rebalance_to_policy(data, policy)}
        assert "AAA" not in trades              # buy suppressed
        assert trades["BBB"].is_buy is False    # overweight, sold
