# finkritintel/tests/integration/test_tax_live.py
"""
Integration tests for finkritintel.integration.finkritq.tax_live.

Uses a mock DataRegistry, no network. Covers both spot-price sources, the
snapshot provider and the history-close fallback used when no snapshot provider
is registered (the offline demo registry).
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import numpy as np

from finkritq.asset import AssetSnapshot
from finkritq.datatype import PriceHistory

from finkritintel.integration.finkritq.tax_live import (
    PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING,
    PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING,
    PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING,
    _portfolio_harvestable_losses_live,
    _portfolio_holding_period_breakdown_live,
    _portfolio_unrealized_gains_live,
)
from finkritintel.tool.tax import (
    PORTFOLIO_HARVESTABLE_LOSSES,
    PORTFOLIO_HOLDING_PERIOD_BREAKDOWN,
    PORTFOLIO_UNREALIZED_GAINS,
)

from .fixtures import make_portfolio_data

# The fixture portfolio: AAA 10 shares and BBB 5 shares, both at cost 100,
# acquired 2020-01-01 (so long term against any recent as_of).
_PORTFOLIO = make_portfolio_data().portfolio
_AS_OF = date(2024, 6, 1)


def _registry_with_snapshots(prices: dict[str, float]) -> MagicMock:
    registry = MagicMock()
    registry.snapshot.side_effect = lambda asset: AssetSnapshot(
        asset=asset, last_price=prices[asset.ticker], previous_close=prices[asset.ticker]
    )
    return registry


def _registry_history_only(prices: dict[str, float]) -> MagicMock:
    # snapshot raises like a registry with no snapshot provider, so the tax
    # helper must fall back to the most recent history close.
    registry = MagicMock()
    registry.snapshot.side_effect = RuntimeError("Snapshot provider has not been registered.")

    def history(asset, **_):
        p = prices[asset.ticker]
        arr = np.array([p * 0.9, p], dtype=float)  # last close is the spot price
        dates = np.array(["2024-05-31", "2024-06-01"], dtype="datetime64[D]")
        return PriceHistory(dates=dates, open=arr, high=arr, low=arr, close=arr,
                            volume=np.ones(2, dtype=np.int64))

    registry.history.side_effect = history
    return registry


class TestTaxLiveContracts:
    def test_bindings_reference_their_contracts(self):
        assert PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING.contract is PORTFOLIO_UNREALIZED_GAINS
        assert PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING.contract is PORTFOLIO_HARVESTABLE_LOSSES
        assert PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING.contract is PORTFOLIO_HOLDING_PERIOD_BREAKDOWN

    def test_bindings_return_dict(self):
        for binding in (
            PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING,
            PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING,
            PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING,
        ):
            assert binding.output_schema is dict


class TestUnrealizedGains:
    def test_gains_and_long_short_split(self):
        # AAA to 150 (+500 gain), BBB to 80 (-100 loss), both long term.
        registry = _registry_with_snapshots({"AAA": 150.0, "BBB": 80.0})
        result = _portfolio_unrealized_gains_live(_PORTFOLIO, registry, as_of=_AS_OF)

        assert result["market_value"] == 1900.0
        assert result["cost_basis"] == 1500.0
        assert result["unrealized_gain"] == 400.0
        assert result["long_term_unrealized_gain"] == 400.0
        assert result["short_term_unrealized_gain"] == 0.0
        assert result["holdings"]["AAA"]["unrealized_gain"] == 500.0
        assert result["holdings"]["BBB"]["unrealized_gain"] == -100.0

    def test_history_fallback_when_no_snapshot_provider(self):
        registry = _registry_history_only({"AAA": 150.0, "BBB": 80.0})
        result = _portfolio_unrealized_gains_live(_PORTFOLIO, registry, as_of=_AS_OF)
        assert result["unrealized_gain"] == 400.0
        registry.snapshot.assert_called()   # tried snapshot first
        registry.history.assert_called()    # then fell back to history


class TestHarvestableLosses:
    def test_finds_the_losing_lot(self):
        registry = _registry_with_snapshots({"AAA": 150.0, "BBB": 80.0})
        result = _portfolio_harvestable_losses_live(_PORTFOLIO, registry, as_of=_AS_OF)

        assert result["total_harvestable_loss"] == 100.0
        assert result["long_term_loss"] == 100.0
        assert result["short_term_loss"] == 0.0
        assert [c["ticker"] for c in result["candidates"]] == ["BBB"]
        assert result["wash_sale_blocked"] == []

    def test_min_loss_threshold_excludes_small_losses(self):
        registry = _registry_with_snapshots({"AAA": 150.0, "BBB": 80.0})
        result = _portfolio_harvestable_losses_live(
            _PORTFOLIO, registry, as_of=_AS_OF, min_loss=200.0
        )
        assert result["candidates"] == []
        assert result["total_harvestable_loss"] == 0.0


class TestHoldingPeriodBreakdown:
    def test_all_long_term(self):
        registry = _registry_with_snapshots({"AAA": 150.0, "BBB": 80.0})
        result = _portfolio_holding_period_breakdown_live(_PORTFOLIO, registry, as_of=_AS_OF)

        assert result["long_term"]["market_value"] == 1900.0
        assert result["short_term"]["market_value"] == 0.0
        assert result["long_term_market_fraction"] == 1.0
