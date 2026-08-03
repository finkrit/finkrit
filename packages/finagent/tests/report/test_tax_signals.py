# finagent/tests/report/test_tax_signals.py
"""
Tax signals composer.

Fixed prices (not the seeded-random fixture provider), so every gain, loss,
and saving asserts to an exact number. as_of 2024-06-01 throughout.

    HARV: 10 @ 100, acquired 2019       -> price 80,  $200 long-term loss, harvestable
    WASH: 10 @ 100, acquired 25d before -> price 80,  loss but wash-sale blocked
    NEAR: 10 @ 100, acquired 340d before -> price 150, gain lot 25d from long term
    NLOS: 10 @ 100, acquired 350d before -> price 90,  loss lot 15d from long term
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

from finkritq.data import DataRegistry
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import PriceHistory
from finkritq.portfolio import Portfolio, Position, TaxLot

from finagent.report import compose_tax_signals
from finagent.tests.fixtures import make_stock

_AS_OF = date(2024, 6, 1)

_PRICES = {"HARV": 80.0, "WASH": 80.0, "NEAR": 150.0, "NLOS": 90.0}


class _FixedPriceProvider(HistoryProvider):
    def history(self, asset, start=None, end=None, interval="1d") -> PriceHistory:
        dates = np.array(
            [np.datetime64("2024-01-02", "D") + np.timedelta64(i, "D") for i in range(30)],
            dtype="datetime64[D]",
        ).astype("datetime64[ns]")
        closes = np.full(30, _PRICES[asset.ticker])
        return PriceHistory(
            dates=dates, open=closes, high=closes, low=closes, close=closes,
            volume=np.ones(30, dtype=np.int64),
        )


def _lot(lot_id: str, acquired: date) -> TaxLot:
    return TaxLot(
        id=lot_id, quantity=Decimal("10"), cost_per_share=Decimal("100"), acquired=acquired
    )


def _setup() -> tuple[Portfolio, DataRegistry]:
    positions = [
        Position(id="p-harv", asset=make_stock("HARV"), lots=(_lot("l-harv", date(2019, 1, 1)),)),
        Position(id="p-wash", asset=make_stock("WASH"), lots=(_lot("l-wash", _AS_OF - timedelta(days=25)),)),
        Position(id="p-near", asset=make_stock("NEAR"), lots=(_lot("l-near", _AS_OF - timedelta(days=340)),)),
        Position(id="p-nlos", asset=make_stock("NLOS"), lots=(_lot("l-nlos", _AS_OF - timedelta(days=350)),)),
    ]
    registry = DataRegistry()
    registry.register_history(_FixedPriceProvider())
    return Portfolio(id="pf", name="signals", positions=positions), registry


class TestComposeTaxSignals:

    def _report(self, **kwargs):
        portfolio, registry = _setup()
        return compose_tax_signals(portfolio, registry, as_of=_AS_OF, **kwargs)

    def test_harvest_signal_carries_lot_detail_and_saving(self):
        report = self._report()
        harv = next(s for s in report.harvest if s.ticker == "HARV")
        assert harv.lot_id == "l-harv"
        assert harv.quantity == 10.0
        assert harv.unrealized_loss == 200.0
        assert harv.is_long_term is True
        # long-term loss at the default long rate: 200 * 0.15
        assert harv.estimated_saving == 30.0

    def test_short_term_loss_priced_at_short_rate(self):
        report = self._report()
        nlos = next(s for s in report.harvest if s.ticker == "NLOS")
        assert nlos.is_long_term is False
        # 100 loss * 0.30
        assert nlos.estimated_saving == 30.0

    def test_wash_sale_blocked_named_not_harvested(self):
        report = self._report()
        assert report.wash_sale_blocked == ["WASH"]
        assert all(s.ticker != "WASH" for s in report.harvest)

    def test_countdown_gain_lot_says_hold(self):
        report = self._report()
        near = next(c for c in report.countdowns if c.ticker == "NEAR")
        assert near.action == "hold"
        assert near.days_until == 25
        assert near.unrealized_gain == 500.0
        # rate spread 0.30 - 0.15 on the $500 gain
        assert near.estimated_saving == 75.0

    def test_countdown_loss_lot_says_harvest_now(self):
        report = self._report()
        nlos = next(c for c in report.countdowns if c.ticker == "NLOS")
        assert nlos.action == "harvest_now"
        assert nlos.days_until == 15
        assert nlos.unrealized_gain == -100.0
        assert nlos.estimated_saving == 15.0

    def test_totals_sum_over_signals(self):
        report = self._report()
        assert report.total_harvestable_loss == 300.0   # 200 + 100
        assert report.estimated_harvest_saving == 60.0  # 30 long + 30 short

    def test_rates_echoed_for_labeling(self):
        report = self._report(short_term_rate=0.35, long_term_rate=0.20)
        assert report.short_term_rate == 0.35
        assert report.long_term_rate == 0.20
        harv = next(s for s in report.harvest if s.ticker == "HARV")
        assert harv.estimated_saving == 40.0  # 200 * 0.20

    def test_inverted_rate_spread_refused(self):
        # short < long would flip the countdown advice, refuse loudly.
        with pytest.raises(ValueError):
            self._report(short_term_rate=0.10, long_term_rate=0.20)

    def test_as_of_echoed(self):
        assert self._report().as_of == _AS_OF
