from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.optimize.harvest import harvest_candidates
from finkritq.portfolio import Portfolio

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.tax import (
    PORTFOLIO_HARVESTABLE_LOSSES,
    PORTFOLIO_HOLDING_PERIOD_BREAKDOWN,
    PORTFOLIO_UNREALIZED_GAINS,
)
from finkritintel.integration.finkritq.tax_schema_live import (
    PortfolioHarvestableLossesLiveInput,
    PortfolioHoldingPeriodBreakdownLiveInput,
    PortfolioUnrealizedGainsLiveInput,
)

# The tax lens works on current spot prices, not price history, so unlike the
# risk and performance live wrappers it reads one price per holding rather than
# a full window. Each wrapper returns a plain, ticker-keyed dict of floats, so
# the result is JSON-serializable, carries no lot internals or client data into
# the model, and needs no output adapter.


def spot_prices(portfolio: Portfolio, registry: DataRegistry) -> dict[Asset, Decimal]:
    # Current price per holding, as a Decimal for the tax-lot math. Prefer the
    # snapshot provider, and fall back to the most recent history close when no
    # snapshot provider is registered (the offline demo registry has history but
    # no snapshot), so the tax tools run against any registry. Public: the
    # rebalance bindings and the finagent signal composer read prices through
    # this too, so every tax-flavored number is computed off the same quote.
    #
    # Fetched in parallel, one worker per holding, matching
    # PortfolioData.from_registry: each quote is an independent network call,
    # and a sequential loop made the tax views wait holdings-times-latency.
    def fetch(position) -> tuple[Asset, Decimal]:
        asset = position.asset
        try:
            last = registry.snapshot(asset).last_price
        except RuntimeError:
            last = float(registry.history(asset).close[-1])
        return asset, Decimal(str(last))

    with ThreadPoolExecutor() as executor:
        return dict(executor.map(fetch, portfolio.positions))


def _money(value) -> float:
    return round(float(value), 2)


def _ratio(value) -> float:
    return round(float(value), 6)


def _portfolio_unrealized_gains_live(
    portfolio: Portfolio, registry: DataRegistry, as_of: date | None = None,
) -> dict:
    as_of = as_of or date.today()
    prices = spot_prices(portfolio, registry)

    holdings: dict[str, dict] = {}
    total_mv = Decimal("0")
    total_cb = Decimal("0")
    long_term_gain = Decimal("0")
    short_term_gain = Decimal("0")

    for position in portfolio.positions:
        price = prices[position.asset]
        mv = Decimal("0")
        cb = Decimal("0")
        for lot in position.lots:
            lot_mv = lot.market_value(price)
            lot_gain = lot_mv - lot.cost_basis
            mv += lot_mv
            cb += lot.cost_basis
            if lot.is_long_term(as_of):
                long_term_gain += lot_gain
            else:
                short_term_gain += lot_gain
        holdings[position.asset.ticker] = {
            "market_value": _money(mv),
            "cost_basis": _money(cb),
            "unrealized_gain": _money(mv - cb),
            "unrealized_return": _ratio((mv - cb) / cb) if cb else 0.0,
        }
        total_mv += mv
        total_cb += cb

    return {
        "as_of": as_of.isoformat(),
        "market_value": _money(total_mv),
        "cost_basis": _money(total_cb),
        "unrealized_gain": _money(total_mv - total_cb),
        "unrealized_return": _ratio((total_mv - total_cb) / total_cb) if total_cb else 0.0,
        "long_term_unrealized_gain": _money(long_term_gain),
        "short_term_unrealized_gain": _money(short_term_gain),
        "holdings": holdings,
    }


def _portfolio_harvestable_losses_live(
    portfolio: Portfolio, registry: DataRegistry, as_of: date | None = None,
    min_loss: float = 0.0, wash_sale_window_days: int = 30,
) -> dict:
    as_of = as_of or date.today()
    prices = spot_prices(portfolio, registry)

    report = harvest_candidates(
        portfolio, prices, as_of,
        min_loss=Decimal(str(min_loss)),
        wash_sale_window_days=wash_sale_window_days,
    )

    candidates = [
        {
            "ticker": candidate.asset.ticker,
            "unrealized_loss": _money(candidate.unrealized_loss),
            "market_value": _money(candidate.market_value),
            "cost_basis": _money(candidate.cost_basis),
            "is_long_term": candidate.is_long_term,
        }
        for candidate in report.candidates
    ]

    return {
        "as_of": as_of.isoformat(),
        "total_harvestable_loss": _money(report.total_harvestable_loss),
        "short_term_loss": _money(report.short_term_loss),
        "long_term_loss": _money(report.long_term_loss),
        "wash_sale_blocked": [asset.ticker for asset in report.wash_sale_blocked],
        "candidates": candidates,
    }


def _portfolio_holding_period_breakdown_live(
    portfolio: Portfolio, registry: DataRegistry, as_of: date | None = None,
) -> dict:
    as_of = as_of or date.today()
    prices = spot_prices(portfolio, registry)

    long_mv = Decimal("0")
    long_cb = Decimal("0")
    short_mv = Decimal("0")
    short_cb = Decimal("0")
    holdings: dict[str, dict] = {}

    for position in portfolio.positions:
        price = prices[position.asset]
        holding_long = Decimal("0")
        holding_short = Decimal("0")
        for lot in position.lots:
            lot_mv = lot.market_value(price)
            if lot.is_long_term(as_of):
                long_mv += lot_mv
                long_cb += lot.cost_basis
                holding_long += lot_mv
            else:
                short_mv += lot_mv
                short_cb += lot.cost_basis
                holding_short += lot_mv
        holdings[position.asset.ticker] = {
            "long_term_market_value": _money(holding_long),
            "short_term_market_value": _money(holding_short),
        }

    total_mv = long_mv + short_mv
    return {
        "as_of": as_of.isoformat(),
        "long_term": {"cost_basis": _money(long_cb), "market_value": _money(long_mv)},
        "short_term": {"cost_basis": _money(short_cb), "market_value": _money(short_mv)},
        "long_term_market_fraction": _ratio(long_mv / total_mv) if total_mv else 0.0,
        "holdings": holdings,
    }


PORTFOLIO_UNREALIZED_GAINS_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_UNREALIZED_GAINS,
    input_schema=PortfolioUnrealizedGainsLiveInput,
    output_schema=dict,
    implementation=_portfolio_unrealized_gains_live,
)

PORTFOLIO_HARVESTABLE_LOSSES_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_HARVESTABLE_LOSSES,
    input_schema=PortfolioHarvestableLossesLiveInput,
    output_schema=dict,
    implementation=_portfolio_harvestable_losses_live,
)

PORTFOLIO_HOLDING_PERIOD_BREAKDOWN_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_HOLDING_PERIOD_BREAKDOWN,
    input_schema=PortfolioHoldingPeriodBreakdownLiveInput,
    output_schema=dict,
    implementation=_portfolio_holding_period_breakdown_live,
)
