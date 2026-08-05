# finkritcore/desk.py
"""
The Desk: where the book, the data feed, and the deterministic work live.

The desk computes, the assistant talks. Everything an integrator or the
dashboard needs happens here with no LLM anywhere in the path: registration,
the risk report, the tax signals, the rebalance comparison, cache prefetch,
and the half of CSV parsing that a labelled file never needs a model for.
Named for the trading floor: a desk is a place with its own book and feed,
staffed to run numbers rather than hold conversations.

``finagent.Assistant`` composes a Desk rather than reimplementing it, so the
chat surface and the dashboard read the same store through the same registry
and cannot disagree on a number. Constructing one costs nothing and requires
no key, which is the point: a caller who only wants the analytics should not
have to install an agent framework to get them.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.data.providers import (
    MemoizingHistoryProvider,
    MemoizingSnapshotProvider,
    YFinanceProvider,
)
from finkritq.datatype import MarketIndex
from finkritq.portfolio import Portfolio

from finkritintel.integration.finkritq import PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING

from finkritcore.ingest import (
    DEFAULT_PORTFOLIO_NAME,
    ParsedPortfolio,
    parse_portfolio_csv_in_code,
)
from finkritcore.report.composer import compose_portfolio_risk_report
from finkritcore.report.metric import RiskMetric
from finkritcore.report.report import PortfolioRiskReport
from finkritcore.report.tax_signals import TaxSignalsReport, compose_tax_signals
from finkritcore.store import InMemoryStore, Store


def default_registry() -> DataRegistry:
    """Live market data, memoized for the session.

    Public because a Desk is constructible on its own, with no
    finagent in sight, and the caller who omits a registry still deserves a
    working one.
    """
    registry = DataRegistry()
    # Session-scoped memoization so repeated questions about the same holdings
    # don't re-download. Persistent caching is a later (v2) layer. Snapshots
    # get a short TTL cache so a prefetch pass and the view reads that follow
    # it share one quote per ticker instead of hitting the network twice.
    provider = MemoizingHistoryProvider(YFinanceProvider())
    registry.register_history(provider)
    registry.register_snapshot(MemoizingSnapshotProvider(YFinanceProvider()))
    return registry


class Desk:
    """
    One store, one registry, and the deterministic work over them.

    ``store`` and ``registry`` are public attributes rather than private: the
    agent layer builds its own dependency object out of exactly these two, and
    hiding them behind accessors would buy nothing.
    """

    def __init__(
        self,
        store: Store | None = None,
        registry: DataRegistry | None = None,
    ) -> None:
        self.store = store or InMemoryStore()
        self.registry = registry or default_registry()
        # The benchmark every risk report betas against has to resolve like any
        # other asset, and no upload will ever register it.
        self.store.register_asset(MarketIndex.SP500.as_asset())

    def register_portfolio(self, portfolio: Portfolio) -> None:
        self.store.register_portfolio(portfolio)

    def register_asset(self, asset: Asset) -> None:
        self.store.register_asset(asset)

    def list_portfolios(self) -> list[Portfolio]:
        return self.store.list_portfolios()

    def report(
        self,
        portfolio_id: str,
        metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
        *,
        benchmark: Asset | None = None,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PortfolioRiskReport:
        # Straight to the composer. The risk agent exposes the same thing for
        # a caller who already holds an agent, but neither goes through a model
        # and neither is built on the other.
        portfolio = self.store.get_portfolio(portfolio_id)
        return compose_portfolio_risk_report(
            portfolio,
            self.registry,
            metrics,
            benchmark=benchmark,
            start=start,
            end=end,
            interval=interval,
        )

    def tax_signals(self, portfolio_id: str, **kwargs) -> TaxSignalsReport:
        # The dashboard's actionable tax view (harvest candidates, wash sale
        # warnings, long term countdowns). kwargs pass through to
        # compose_tax_signals (rates, thresholds, as_of).
        portfolio = self.store.get_portfolio(portfolio_id)
        return compose_tax_signals(portfolio, self.registry, **kwargs)

    def rebalance_compare(self, portfolio_id: str, **kwargs) -> dict:
        # The same fixed strategy menu the chat compare tool runs (full,
        # band_edge, partial_fill), served through the identical intel binding
        # so the two surfaces can never disagree on a number. kwargs pass
        # through to the binding (objective, gain_budget, tolerance, method,
        # as_of).
        portfolio = self.store.get_portfolio(portfolio_id)
        return PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING.execute(
            portfolio=portfolio, registry=self.registry, **kwargs
        )

    def prefetch_events(self, portfolio_id: str):
        """
        Warm the data caches for one portfolio, yielding a progress event per
        ticker as its download lands.

        Downloads run in parallel (one worker per ticker) and each event is
        emitted on completion, so a consumer can render a live progress bar.
        Warms exactly what the dashboard endpoints read: the default-window
        price history (same memoizer key) and the spot snapshot (TTL cache),
        plus the S&P 500 benchmark the risk report betas against. A ticker
        that fails reports status "error" with the reason and does not stop
        the rest, mirroring the partial-success rule reports follow.

        The portfolio lookup happens eagerly (a miss raises before any event),
        the download fan-out lazily on iteration.
        """
        portfolio = self.store.get_portfolio(portfolio_id)
        assets = [position.asset for position in portfolio.positions]
        assets.append(MarketIndex.SP500.as_asset())

        registry = self.registry

        def events():
            yield {"event": "start", "tickers": [asset.ticker for asset in assets]}

            def warm(asset: Asset) -> None:
                registry.history(asset)
                try:
                    registry.snapshot(asset)
                except RuntimeError:
                    # No snapshot provider registered (offline registry): the
                    # tax tools fall back to history, already warmed above.
                    pass

            with ThreadPoolExecutor() as executor:
                futures = {executor.submit(warm, asset): asset for asset in assets}
                for future in as_completed(futures):
                    asset = futures[future]
                    try:
                        future.result()
                        yield {"ticker": asset.ticker, "status": "ready"}
                    except Exception as exc:  # noqa: BLE001 - reported, not raised
                        yield {"ticker": asset.ticker, "status": "error", "detail": str(exc)}

            yield {"event": "end"}

        return events()

    def parse_portfolio_csv(
        self, csv_text: str, name: str = DEFAULT_PORTFOLIO_NAME
    ) -> ParsedPortfolio | None:
        """The extracted holdings, or None when the file needs a model.

        None rather than an exception: core has no opinion about models and no
        way to reach one. Deciding what an unreadable file costs belongs to the
        caller, which is ``Assistant.parse_portfolio_csv`` for anyone who has
        an agent, and the integrator themselves for anyone who does not.

        Registers nothing. The caller reviews and corrects, then registers.
        """
        return parse_portfolio_csv_in_code(csv_text, name)
