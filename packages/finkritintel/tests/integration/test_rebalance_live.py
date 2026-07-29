# finkritintel/tests/integration/test_rebalance_live.py
"""
Integration tests for the live tax-aware rebalance binding.

Uses a mock DataRegistry serving the deterministic fixture histories, no
network. The finkritq plan loop has its own unit tests, so these cover the
composition: optimizer target computed in code, budget semantics surfaced
correctly, and an output the agent edge can serialize.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from finkritq.datatype import LotSaleMethod
from finkritq.portfolio import Portfolio, Position, TaxLot

from finkritintel.integration.finkritq.rebalance_live import (
    PORTFOLIO_TAX_AWARE_REBALANCE_LIVE_BINDING,
    _portfolio_tax_aware_rebalance_live,
)
from finkritintel.tool.rebalance import PORTFOLIO_TAX_AWARE_REBALANCE

from .fixtures import make_portfolio_data

_AS_OF = date(2024, 6, 1)

# The fixture PortfolioData carries the histories keyed by asset. The registry
# mock serves those same histories, and no snapshot provider, so spot prices
# fall back to the last close and agree with the data the optimizer saw.
_DATA = make_portfolio_data()


def _mixed_lot_portfolio() -> Portfolio:
    # Rebuild the fixture portfolio with lot structure worth testing: AAA holds
    # a long-term lot with an embedded gain (cost 50) and a recent short-term
    # lot with an embedded loss (cost 500, far above any fixture price), BBB
    # stays a single long-term lot at cost 100.
    positions = []
    for position in _DATA.portfolio.positions:
        if position.asset.ticker == "AAA":
            lots = (
                TaxLot(id="lot-a-old", quantity=Decimal("6"),
                       cost_per_share=Decimal("50"), acquired=date(2020, 1, 1)),
                TaxLot(id="lot-a-new", quantity=Decimal("4"),
                       cost_per_share=Decimal("500"), acquired=date(2024, 3, 1)),
            )
        else:
            lots = position.lots
        positions.append(Position(id=position.id, asset=position.asset, lots=lots))
    return Portfolio(id="port-1", name="Test Portfolio", positions=positions)


def _registry() -> MagicMock:
    registry = MagicMock()
    registry.snapshot.side_effect = RuntimeError("Snapshot provider has not been registered.")
    registry.history.side_effect = lambda asset, **_: _DATA._histories[asset]
    return registry


_PORTFOLIO = _mixed_lot_portfolio()


def _run(**kwargs) -> dict:
    return _portfolio_tax_aware_rebalance_live(
        _PORTFOLIO, _registry(), as_of=_AS_OF, **kwargs
    )


class TestValidation:

    def test_unknown_objective_is_rejected_with_the_allowed_names(self):
        with pytest.raises(ValueError, match="min_variance.*max_sharpe"):
            _run(objective="sharpest")

    def test_negative_budget_is_rejected(self):
        with pytest.raises(ValueError, match="zero or positive"):
            _run(gain_budget=-100.0)


class TestPlanShape:

    def test_output_is_json_serializable(self):
        # The agent edge sends this to the model verbatim, a Decimal or Asset
        # leaking through would fail there instead of here.
        json.dumps(_run())

    def test_gains_split_adds_up(self):
        plan = _run()
        assert plan["realized_gain"] == pytest.approx(
            plan["short_term_gain"] + plan["long_term_gain"], abs=0.01
        )

    def test_target_weights_are_ticker_keyed_and_sum_to_one(self):
        plan = _run()
        assert set(plan["target_weights"]) <= {"AAA", "BBB"}
        assert sum(plan["target_weights"].values()) == pytest.approx(1.0, abs=1e-4)

    def test_every_sell_names_its_lot_count_and_value(self):
        plan = _run()
        assert plan["sells"], "the fixture drift should produce at least one sell"
        for sell in plan["sells"]:
            assert sell["lots_touched"] >= 1
            assert sell["sell_value"] > 0

    def test_method_and_objective_echo_back(self):
        plan = _run(objective="max_sharpe", method=LotSaleMethod.FIFO)
        assert plan["objective"] == "max_sharpe"
        assert plan["method"] == "fifo"


class TestBudgetSemantics:

    def test_unlimited_budget_defers_nothing(self):
        plan = _run(gain_budget=None)
        assert plan["deferred"] == []
        assert plan["gain_budget"] is None

    def test_zero_budget_realizes_no_net_gain(self):
        # A zero budget is the pure harvesting mode: losses still realize,
        # any sell that nets a gain is deferred instead.
        plan = _run(gain_budget=0.0)
        for sell in plan["sells"]:
            assert sell["realized_gain"] <= 0
        assert plan["realized_gain"] <= 0

    def test_deferred_and_executed_never_overlap(self):
        plan = _run(gain_budget=0.0)
        executed = {sell["ticker"] for sell in plan["sells"]}
        assert executed.isdisjoint(set(plan["deferred"]))


def test_binding_carries_the_contract():
    assert PORTFOLIO_TAX_AWARE_REBALANCE_LIVE_BINDING.contract is PORTFOLIO_TAX_AWARE_REBALANCE
    assert PORTFOLIO_TAX_AWARE_REBALANCE.name == "portfolio_tax_aware_rebalance"


class TestSizingAndPartialFill:

    def test_sizing_and_partial_fill_echo_back(self):
        from finkritq.datatype import RebalanceSizing
        plan = _run(sizing=RebalanceSizing.TO_BAND_EDGE, tolerance=0.02, partial_fill=True)
        assert plan["sizing"] == "to_band_edge"
        assert plan["partial_fill"] is True

    def test_band_edge_without_a_band_reaches_the_model_as_a_domain_error(self):
        # The core raises ValueError, which the agent edge turns into a
        # ModelRetry. Here we just assert it surfaces as ValueError with the
        # corrective message rather than as a silent full rebalance.
        from finkritq.datatype import RebalanceSizing
        with pytest.raises(ValueError, match="positive tolerance"):
            _run(sizing=RebalanceSizing.TO_BAND_EDGE)

    def test_every_sell_carries_partial_and_executed_value(self):
        plan = _run()
        for sell in plan["sells"]:
            assert "is_partial" in sell
            assert sell["executed_value"] > 0

    def test_residual_drift_is_reported_and_bounded(self):
        plan = _run()
        assert 0.0 <= plan["residual_drift"] <= 1.0


class TestCompare:

    def _compare(self, **kwargs) -> dict:
        from finkritintel.integration.finkritq.rebalance_live import (
            _portfolio_rebalance_compare_live,
        )
        return _portfolio_rebalance_compare_live(
            _PORTFOLIO, _registry(), as_of=_AS_OF, **kwargs
        )

    def test_returns_every_named_strategy_with_the_shared_header(self):
        from finkritq.optimize import REBALANCE_STRATEGIES
        result = self._compare()
        assert set(result["strategies"]) == set(REBALANCE_STRATEGIES)
        assert set(result["target_weights"]) <= {"AAA", "BBB"}
        assert result["tolerance"] == pytest.approx(0.02)

    def test_output_is_json_serializable(self):
        json.dumps(self._compare())

    def test_rows_share_the_plan_shape(self):
        # A row must look exactly like a single-plan body, so the UI renders
        # both with one component and the two tools cannot drift apart.
        single = _run()
        result = self._compare()
        row_keys = set(result["strategies"]["full"])
        single_plan_keys = row_keys & set(single)
        assert {"sells", "deferred", "realized_gain", "residual_drift"} <= single_plan_keys

    def test_zero_budget_rows_differ_in_the_documented_way(self):
        # With no gain room, full defers the gain-sell whole while partial_fill
        # can only do the same or better (a loss-prefix fill), never worse.
        result = self._compare(gain_budget=0.0)
        full = result["strategies"]["full"]
        partial = result["strategies"]["partial_fill"]
        assert full["realized_gain"] <= 0
        assert partial["realized_gain"] <= 0
        assert partial["residual_drift"] <= full["residual_drift"] + 1e-9

    def test_zero_tolerance_is_rejected(self):
        with pytest.raises(ValueError, match="positive tolerance"):
            self._compare(tolerance=0.0)

    def test_binding_carries_the_contract(self):
        from finkritintel.integration.finkritq.rebalance_live import (
            PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING,
        )
        from finkritintel.tool.rebalance import PORTFOLIO_REBALANCE_COMPARE
        assert PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING.contract is PORTFOLIO_REBALANCE_COMPARE
        assert PORTFOLIO_REBALANCE_COMPARE.name == "portfolio_rebalance_compare"
