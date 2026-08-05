# finkritcore/tests/test_desk.py
"""
Desk, the deterministic facade.

The point of these is the absence of a model. Every test here constructs the
desk with nothing but a store and a fake registry, so if anything on this
path ever reaches for an agent or a key, it fails here rather than in a user's
upload.
"""
from __future__ import annotations

from finkritq.data import DataRegistry
from finkritq.data.providers import (
    MemoizingHistoryProvider,
    MemoizingSnapshotProvider,
    YFinanceProvider,
)

from finkritcore.report.report import PortfolioRiskReport
from finkritcore.desk import Desk, default_registry
from finkritcore.store import InMemoryStore
from finkritcore.tests.fixtures import make_portfolio, make_registry


def _desk() -> Desk:
    return Desk(store=InMemoryStore(), registry=make_registry())


class TestConstruction:

    def test_it_needs_no_model_and_no_key(self):
        # The whole reason core exists. No argument here can carry one.
        desk = _desk()
        assert isinstance(desk.store, InMemoryStore)

    def test_it_registers_the_benchmark(self):
        # Every risk report betas against the S&P 500 and no upload will ever
        # register it, so the desk has to.
        desk = _desk()
        assert desk.store.get_asset("^GSPC").ticker == "^GSPC"

    def test_it_defaults_both_collaborators(self):
        desk = Desk()
        assert isinstance(desk.store, InMemoryStore)
        assert isinstance(desk.registry, DataRegistry)


class TestDeterministicSurface:

    def test_report_reaches_the_composer_without_an_agent(self):
        desk = _desk()
        desk.register_portfolio(make_portfolio("port-1"))
        report = desk.report("port-1")
        assert isinstance(report, PortfolioRiskReport)

    def test_registering_a_portfolio_makes_it_listable(self):
        desk = _desk()
        desk.register_portfolio(make_portfolio("port-1"))
        assert [p.id for p in desk.list_portfolios()] == ["port-1"]


class TestParseCsv:
    """Core answers or declines. It never raises about models, because it has
    no way to reach one and no opinion about whether the caller can."""

    def test_a_labelled_header_is_answered(self):
        parsed = _desk().parse_portfolio_csv("Symbol,Shares,Cost,Date\nAAPL,10,150,2023-01-15")
        assert parsed is not None
        assert parsed.holdings[0].ticker == "AAPL"

    def test_an_ambiguous_header_declines_rather_than_raising(self):
        assert _desk().parse_portfolio_csv("Symbol,Shares\nAAPL,10") is None

    def test_it_registers_nothing(self):
        # Parse only. The caller reviews and corrects, then registers.
        desk = _desk()
        desk.parse_portfolio_csv("Symbol,Shares,Cost,Date\nAAPL,10,150,2023-01-15")
        assert desk.list_portfolios() == []


class TestDefaultRegistry:
    """
    default_registry() wires YFinanceProvider + MemoizingHistoryProvider.
    Construction never hits the network (only .history()/.snapshot() calls
    would), so this is safe to test directly without a live fetch.
    """

    def test_returns_a_data_registry(self):
        assert isinstance(default_registry(), DataRegistry)

    def test_history_provider_is_memoized(self):
        registry = default_registry()
        assert isinstance(registry._history_provider, MemoizingHistoryProvider)

    def test_memoized_provider_wraps_yfinance(self):
        registry = default_registry()
        assert isinstance(registry._history_provider._wrapped, YFinanceProvider)

    def test_snapshot_provider_is_ttl_cached_over_yfinance(self):
        # Snapshots carry a short TTL cache (not the day-keyed history memo):
        # a prefetch pass and the view reads that follow it must share one
        # quote per ticker instead of hitting the network twice, while a later
        # interaction still gets a fresh price.
        registry = default_registry()
        assert isinstance(registry._snapshot_provider, MemoizingSnapshotProvider)
        assert isinstance(registry._snapshot_provider._wrapped, YFinanceProvider)
