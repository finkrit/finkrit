# finkrit/packages/finkritq/main.py
"""
Runnable example: run every finkritq analytic pillar (risk, performance,
optimization, tax) over a portfolio, printing the results to the terminal.

Two data sources, same report:

    python -m finkritq              fake, seeded, offline synthetic market
    python -m finkritq fake         same as above (explicit)
    python -m finkritq real         live daily data downloaded per ticker
    python -m finkritq real NVDA KO PG --benchmark SPY --years 3

Fake mode needs no network and is fully reproducible (seed 0): asset returns
are driven by a shared market factor plus idiosyncratic noise, so beta and the
benchmark-relative metrics are meaningful. Real mode downloads adjusted daily
closes through the registered history provider and runs the identical analytics
on live prices. Holdings and tax lots are always illustrative (you cannot
download someone's share count or cost basis), but in real mode the cost basis
is anchored to the downloaded prices so gains, losses, and harvest candidates
reflect real moves.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import numpy as np

from finkritq.anal.performance import (
    brinson_attribution,
    money_weighted_return,
    portfolio_annualized_return,
    portfolio_calmar_ratio,
    portfolio_information_ratio,
    portfolio_jensens_alpha,
    portfolio_sharpe_ratio,
    portfolio_sortino_ratio,
    portfolio_total_return,
    portfolio_treynor_ratio,
    time_weighted_return,
    total_return_from_prices,
)
from finkritq.anal.risk import (
    exposure_by_group,
    portfolio_beta,
    portfolio_concentration,
    portfolio_conditional_value_at_risk,
    portfolio_downside_deviation,
    portfolio_maximum_drawdown,
    portfolio_semivariance,
    portfolio_value_at_risk,
    portfolio_variance,
    portfolio_volatility,
)
from finkritq.asset import Stock
from finkritq.data.registry import DataRegistry
from finkritq.datatype import Currency, Exchange, PriceHistory, VaREstimationMethod
from finkritq.policy import (
    DriftBand,
    Policy,
    Restriction,
    RestrictionKind,
    RiskTolerance,
    policy_status,
    suitability,
)
from finkritq.optimize import (
    LotSaleMethod,
    efficient_frontier_portfolio,
    harvest_candidates,
    invest_cashflow,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    rebalance_to_model,
    select_lots_to_sell,
    tax_aware_rebalance,
    total_drift,
)
from finkritq.portfolio import Portfolio, PortfolioData, Position, TaxLot

_N = 120        # return intervals in fake mode -> 121 price observations
_AS_OF = date(2024, 5, 1)   # fake-mode reference date for holding-period / wash-sale

# A small sector lookup so the default real basket buckets sensibly. Anything not
# listed falls back to "Equity" (see _sector_of).
_KNOWN_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Communication", "META": "Communication",
    "JPM": "Financials", "BAC": "Financials",
    "XOM": "Energy", "CVX": "Energy",
    "JNJ": "Healthcare", "PFE": "Healthcare",
    "KO": "Staples", "PG": "Staples", "WMT": "Staples",
}
_DEFAULT_BASKET = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META",   # tech / communication
    "JPM", "XOM", "JNJ", "KO", "WMT",          # financials, energy, healthcare, staples
]
_DEFAULT_BENCHMARK = "SPY"
# A concrete historical window so the default run is reproducible and does not
# depend on the calendar. Override with --start / --end.
_DEFAULT_START = date(2022, 1, 3)
_DEFAULT_END = date(2024, 12, 31)


def _stock(ticker: str) -> Stock:
    return Stock(ticker=ticker, currency=Currency.USD, exchange=Exchange.NASDAQ,
                 company_name=f"{ticker} Corp")


# ---------------------------------------------------------------------------
# Fake source: a synthetic, seeded market (no network)
# ---------------------------------------------------------------------------

def _dates(n: int) -> np.ndarray:
    base = np.datetime64("2024-01-02", "D")
    return np.array([base + np.timedelta64(i, "D") for i in range(n)], dtype="datetime64[D]")


def _history(close: np.ndarray) -> PriceHistory:
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    return PriceHistory(
        dates=_dates(n),
        open=close, high=close, low=close, close=close,
        volume=np.ones(n, dtype=np.int64),
    )


def _fake_position(stock: Stock, quantity: str, position_id: str, lot_id: str) -> Position:
    # Two lots per position so the tax features have something to chew on: an old
    # cheap long-term lot (a gain) and a recent expensive lot (a likely loss that
    # is harvestable, and the one HIFO sells first).
    half = Decimal(quantity) / 2
    lots = (
        TaxLot(id=f"{lot_id}-old", quantity=half, cost_per_share=Decimal("85"), acquired=date(2022, 1, 3)),
        TaxLot(id=f"{lot_id}-new", quantity=half, cost_per_share=Decimal("130"), acquired=date(2024, 3, 15)),
    )
    return Position(id=position_id, asset=stock, lots=lots)


def build_synthetic() -> tuple[PortfolioData, PriceHistory, date, dict[str, str]]:
    rng = np.random.default_rng(0)
    market = rng.normal(0.0009, 0.008, _N)  # market factor per-period returns

    def series(beta: float, drift: float, idio: float) -> np.ndarray:
        r = drift + beta * market + rng.normal(0.0, idio, _N)
        return 100.0 * np.exp(np.cumsum(np.insert(r, 0, 0.0)))

    aaa, bbb, ccc = _stock("AAA"), _stock("BBB"), _stock("CCC")
    positions = [
        _fake_position(aaa, "100", "p-aaa", "l-aaa"),
        _fake_position(bbb, "50", "p-bbb", "l-bbb"),
        _fake_position(ccc, "75", "p-ccc", "l-ccc"),
    ]
    portfolio = Portfolio(id="demo", name="Demo Portfolio (synthetic)", positions=positions)

    histories = {
        aaa: _history(series(beta=1.2, drift=0.0004, idio=0.008)),
        bbb: _history(series(beta=0.8, drift=0.0006, idio=0.010)),
        ccc: _history(series(beta=1.0, drift=0.0005, idio=0.006)),
    }
    data = PortfolioData(portfolio=portfolio, _histories=histories)

    benchmark = _history(1000.0 * np.exp(np.cumsum(np.insert(market, 0, 0.0))))
    sectors = {"AAA": "Technology", "BBB": "Financials", "CCC": "Technology"}
    return data, benchmark, _AS_OF, sectors


# ---------------------------------------------------------------------------
# Real source: live daily data through the history provider
# ---------------------------------------------------------------------------

def _to_date(dt64: np.datetime64) -> date:
    # A single observation date from a history, as a datetime.date.
    return np.datetime64(dt64, "D").astype(object)


def _real_position(stock: Stock, history: PriceHistory, idx: int) -> Position:
    # Illustrative holding whose buys are REAL: each lot is acquired on an actual
    # trading day inside the downloaded window and its cost basis is that day's
    # actual close, so a lot's gain or loss is exactly what the market did between
    # the buy and the last close. No fabricated tilt, some holdings will show a
    # gain and some a loss depending on the tape.
    #
    # Two lots per position, staggered by `idx` so the book looks bought over time
    # rather than all on one day:
    #   old lot  an early-window trading day  -> long-term (held over a year)
    #   new lot  a recent trading day         -> short-term (held under a year)
    dates = history.dates
    close = history.close
    n = len(close)

    old_i = min(5 + idx * 4, n // 4)               # early window, staggered
    new_i = max(n - 1 - (20 + idx * 8), n // 2)     # last few months, staggered

    old_qty = Decimal(str(40 + idx * 5))            # vary share counts across holdings
    new_qty = Decimal(str(20 + idx * 3))

    lots = (
        TaxLot(id=f"{stock.ticker}-old", quantity=old_qty,
               cost_per_share=Decimal(str(round(float(close[old_i]), 2))),
               acquired=_to_date(dates[old_i])),
        TaxLot(id=f"{stock.ticker}-new", quantity=new_qty,
               cost_per_share=Decimal(str(round(float(close[new_i]), 2))),
               acquired=_to_date(dates[new_i])),
    )
    return Position(id=f"p-{stock.ticker}", asset=stock, lots=lots)


def build_real(
    tickers: list[str],
    benchmark_ticker: str,
    start: date,
    end: date,
) -> tuple[PortfolioData, PriceHistory, date, dict[str, str]]:
    # Lazy import so fake mode never needs the network stack, and a missing
    # dependency produces a clear message instead of an import traceback at startup.
    try:
        from finkritq.data.providers import YFinanceProvider
    except ImportError as exc:
        raise SystemExit(
            "Real mode needs the data-provider dependencies. Install them in your "
            f"environment (for example: pip install yfinance pandas loguru). [{exc}]"
        ) from exc

    registry = DataRegistry()
    registry.register_history(YFinanceProvider())

    stocks = [_stock(ticker) for ticker in tickers]

    # Download every holding and the benchmark concurrently: these are
    # independent network calls, so fetching them in a thread pool turns N
    # round-trips into roughly one. executor.map preserves input order, so the
    # results line up with `to_fetch` without any bookkeeping. Cap the pool so a
    # large basket does not open an unbounded number of connections at once.
    def fetch(stock: Stock) -> PriceHistory:
        return registry.history(stock, start=start, end=end)

    to_fetch = stocks + [_stock(benchmark_ticker)]
    with ThreadPoolExecutor(max_workers=min(len(to_fetch), 8)) as executor:
        fetched = list(executor.map(fetch, to_fetch))
    raw, benchmark = fetched[:-1], fetched[-1]

    # Align the holdings to a common calendar so PortfolioData is happy and every
    # series covers identical dates.
    aligned = PriceHistory.align_many(raw)
    histories = dict(zip(stocks, aligned))

    as_of = end
    positions = [_real_position(stock, histories[stock], idx)
                 for idx, stock in enumerate(stocks)]
    portfolio = Portfolio(
        id="live",
        name=f"Live Portfolio ({', '.join(tickers)})",
        positions=positions,
    )
    data = PortfolioData(portfolio=portfolio, _histories=histories)

    sectors = {ticker: _KNOWN_SECTORS.get(ticker, "Equity") for ticker in tickers}
    return data, benchmark, as_of, sectors


# ---------------------------------------------------------------------------
# Reporting (shared by both sources, generalized to any number of holdings)
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


def _row(label: str, value: float, pct: bool = False) -> None:
    shown = f"{value * 100:8.2f}%" if pct else f"{value:9.4f}"
    print(f"  {label:<28} {shown}")


def _weights(label: str, weights: dict) -> None:
    print(f"  {label}")
    for asset, w in weights.items():
        print(f"    {asset.ticker:<6} {w * 100:7.2f}%")


def _note(text: str) -> None:
    # One-line caption explaining the operation whose output follows.
    print(f"  > {text}")


def report(
    data: PortfolioData,
    benchmark: PriceHistory,
    as_of: date,
    sectors: dict[str, str],
) -> None:
    assets = data.assets
    # Equal-weight target model, so drift and rebalance trades are meaningful for
    # any basket without hand-picking numbers per run.
    model = {asset: 1.0 / len(assets) for asset in assets}

    _header("PORTFOLIO")
    print(f"  {data.portfolio.name}: {data.portfolio.position_count} positions, "
          f"{len(data)} observations, {data.start} -> {data.end}")
    _weights("current weights (by market value)", data.weights)

    _header("RISK")
    _row("volatility (annualized)", portfolio_volatility(data), pct=True)
    _row("variance (annualized)", portfolio_variance(data))
    _row("semivariance", portfolio_semivariance(data))
    _row("downside deviation", portfolio_downside_deviation(data), pct=True)
    _row("value at risk (95%)", portfolio_value_at_risk(data), pct=True)
    _row("conditional VaR (95%)", portfolio_conditional_value_at_risk(data), pct=True)
    _row("maximum drawdown", portfolio_maximum_drawdown(data), pct=True)
    _row("beta (vs benchmark)", portfolio_beta(data, benchmark))

    _header("PERFORMANCE")
    _row("total return", portfolio_total_return(data), pct=True)
    _row("annualized return", portfolio_annualized_return(data), pct=True)
    _row("sharpe ratio", portfolio_sharpe_ratio(data))
    _row("sortino ratio", portfolio_sortino_ratio(data))
    _row("calmar ratio", portfolio_calmar_ratio(data))
    _row("treynor ratio", portfolio_treynor_ratio(data, benchmark))
    _row("information ratio", portfolio_information_ratio(data, benchmark))
    _row("jensen's alpha", portfolio_jensens_alpha(data, benchmark), pct=True)

    _header("OPTIMIZATION (allocation)")
    _weights("minimum-variance weights", minimum_variance_portfolio(data))
    _weights("maximum-sharpe weights", maximum_sharpe_portfolio(data, risk_free_rate=0.02))
    print("  efficient frontier (return -> volatility)")
    for point in efficient_frontier_portfolio(data, n_points=5):
        print(f"    {point.expected_return * 100:7.2f}%  ->  {point.volatility * 100:7.2f}%")

    _header("REBALANCING & TAX")
    _note("drift-band rebalance: sell overweights and buy underweights back to the target model")
    print(f"  total drift from equal-weight model: {total_drift(data, model) * 100:.2f}%")
    print("  rebalance trades (drift-ranked):")
    for trade in rebalance_to_model(data, model):
        side = "BUY " if trade.is_buy else "SELL"
        print(f"    {side} {trade.asset.ticker:<5} ${abs(trade.trade_value):>10,.0f}"
              f"   (drift {trade.drift * 100:+.1f}%)")

    prices = {asset: Decimal(str(round(price, 2))) for asset, price in data.latest_prices.items()}
    _note("tax-loss harvesting: lots sitting far enough in the red to realize, wash-sale aware")
    harvest = harvest_candidates(data.portfolio, prices, as_of)
    print(f"  tax-loss harvest: ${harvest.total_harvestable_loss:,.0f} harvestable"
          f"  (ST ${harvest.short_term_loss:,.0f} / LT ${harvest.long_term_loss:,.0f})")
    for candidate in harvest.candidates:
        term = "LT" if candidate.is_long_term else "ST"
        print(f"    {candidate.asset.ticker:<5} lot {candidate.lot.id:<12}"
              f" loss ${candidate.unrealized_loss:>8,.0f}  ({term})")

    first = data.portfolio.positions[0]
    _note("lot selection: which tax lots a sale draws from (HIFO takes highest cost first)")
    sale = select_lots_to_sell(
        first, first.quantity / 2, prices[first.asset], as_of, method=LotSaleMethod.HIFO
    )
    print(f"  HIFO sell {sale.quantity_sold} {first.asset.ticker}:"
          f" realized ${sale.realized_gain:,.0f}"
          f"  (ST ${sale.short_term_gain:,.0f} / LT ${sale.long_term_gain:,.0f})")

    _note("cash-flow investing: put new cash into the underweights only, no full-book churn")
    plan = invest_cashflow(data, model, cash=50_000.0, set_aside=5_000.0)
    print(f"  cash deposit $50,000 (hold back $5,000) -> deploy ${plan.cash_deployed:,.0f}:")
    for trade in plan.trades:
        print(f"    BUY  {trade.asset.ticker:<5} ${trade.trade_value:>10,.0f}")

    _note("tax-aware rebalance: move toward the model but cap realized gains, harvest to fund it")
    budgeted = tax_aware_rebalance(data, model, prices, as_of, gain_budget=200.0)
    deferred = f", deferred {[a.ticker for a in budgeted.deferred]}" if budgeted.deferred else ""
    print(f"  tax-budgeted rebalance (gain budget $200):"
          f" realized ${budgeted.realized_gain:,.0f}, harvested ${budgeted.harvested_loss:,.0f}{deferred}")

    _header("RETURNS WITH FLOWS (TWR vs MWR)")
    _note("an investor drip-feeds cash over time, so the two return measures diverge")
    actual = np.asarray(data.value, dtype=np.float64)
    n = len(actual)
    flows = np.zeros(n)
    actual_with_flow = actual.copy()
    # Recurring contributions, like an investor adding cash every so often. Each
    # deposit buys into the portfolio and earns its return from that point on, so
    # a contribution at t adds C * (V[s]/V[t]) to every later value V[s], not a
    # dead lump of cash. Sizing the deposit off the starting value keeps it
    # proportional across baskets of any size.
    contribution = round(actual[0] * 0.05, -2)
    step = max(n // 9, 1)                       # about eight deposits across the window
    for t in range(step, n, step):
        flows[t] = contribution
        actual_with_flow[t:] += contribution * (actual[t:] / actual[t])
    n_deposits = int(np.count_nonzero(flows))
    print(f"  {n_deposits} contributions of ${contribution:,.0f} "
          f"(${flows.sum():,.0f} added over the window, annualized):")
    _row("time-weighted (manager skill)",
         time_weighted_return(actual_with_flow, flows, annualized=True), pct=True)
    _row("money-weighted / IRR (owner)",
         money_weighted_return(actual_with_flow, flows, annualized=True), pct=True)

    _header("ATTRIBUTION (allocation vs selection)")
    portfolio_returns = {asset: total_return_from_prices(data[asset].close) for asset in assets}
    benchmark_close = data.aligned_close(benchmark)   # benchmark sampled on portfolio dates
    benchmark_return = total_return_from_prices(benchmark_close)
    benchmark_returns = {asset: benchmark_return for asset in assets}
    attribution = brinson_attribution(data.weights, model, portfolio_returns, benchmark_returns)
    _row("allocation effect", attribution.allocation, pct=True)
    _row("selection effect", attribution.selection, pct=True)
    _row("interaction effect", attribution.interaction, pct=True)
    _row("active return (total)", attribution.active_return, pct=True)

    _header("EXPOSURE & CONCENTRATION")
    concentration = portfolio_concentration(data)
    _row("herfindahl index", concentration.herfindahl)
    _row("effective holdings", concentration.effective_holdings)
    _row("largest position", concentration.max_weight, pct=True)
    exposure = exposure_by_group(data.weights, lambda asset: sectors.get(asset.ticker, "Equity"))
    print("  sector exposure:")
    for sector, weight in sorted(exposure.items(), key=lambda kv: kv[1], reverse=True):
        print(f"    {sector:<14} {weight * 100:6.2f}%")

    _header("SUPERVISION (policy & suitability)")
    # Supervise the portfolio against a policy: the equal-weight model with a 5%
    # drift band, a concentration cap on the largest holding, and a comfort band
    # for how much the owner will tolerate losing.
    top_asset = max(data.weights, key=data.weights.get)
    policy = Policy(
        target_weights=model,
        default_band=DriftBand(absolute=0.05),
        restrictions=(Restriction(top_asset, RestrictionKind.MAX_WEIGHT, limit=0.30),),
        risk_tolerance=RiskTolerance(floor_return=-0.15, ceiling_return=0.25),
    )

    _note("drift and restriction check against the model (breaches are the exceptions)")
    status = policy_status(data, policy)
    print(f"  in compliance: {status.in_compliance}   total drift {status.total_drift * 100:.1f}%")
    for breach in status.drift_breaches:
        print(f"    DRIFT {breach.asset.ticker:<5} {breach.current_weight * 100:5.1f}%"
              f" vs {breach.target_weight * 100:5.1f}% target"
              f"   (drift {breach.drift * 100:+.1f}%, band {breach.allowed * 100:.1f}%)")
    for violation in status.restriction_violations:
        print(f"    RULE  {violation.restriction.asset.ticker:<5} {violation.detail}")

    _note("suitability: projected 6-month range vs the owner's comfort band")
    tolerance = policy.risk_tolerance
    for method in (VaREstimationMethod.PARAMETRIC, VaREstimationMethod.HISTORICAL):
        fit = suitability(data, tolerance, method=method)
        print(f"    {method.value:<11} range [{fit.portfolio_floor * 100:+.1f}%,"
              f" {fit.portfolio_ceiling * 100:+.1f}%]"
              f"  tolerance [{tolerance.floor_return * 100:+.1f}%,"
              f" {tolerance.ceiling_return * 100:+.1f}%]"
              f"  -> {fit.verdict.value}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _banner(source: str) -> None:
    line = "=" * 60
    print(line)
    print(f"  finkritq analytics demo   source: {source}")
    print(line)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m finkritq",
        description="Run every finkritq pillar over a fake or a live portfolio.",
    )
    parser.add_argument("mode", nargs="?", choices=["fake", "real"], default="fake",
                        help="fake = offline seeded market (default), real = live download")
    parser.add_argument("tickers", nargs="*",
                        help=f"real-mode tickers (default: {' '.join(_DEFAULT_BASKET)})")
    parser.add_argument("--benchmark", default=_DEFAULT_BENCHMARK,
                        help=f"real-mode benchmark ticker (default: {_DEFAULT_BENCHMARK})")
    parser.add_argument("--start", type=date.fromisoformat, default=_DEFAULT_START,
                        help=f"real-mode window start, YYYY-MM-DD (default: {_DEFAULT_START})")
    parser.add_argument("--end", type=date.fromisoformat, default=_DEFAULT_END,
                        help=f"real-mode window end, YYYY-MM-DD (default: {_DEFAULT_END})")
    args = parser.parse_args(argv)

    if args.mode == "real":
        tickers = args.tickers or _DEFAULT_BASKET
        if args.start >= args.end:
            parser.error(f"--start ({args.start}) must be before --end ({args.end})")
        _banner(f"live download, {len(tickers)} holdings, {args.start} -> {args.end}, "
                f"benchmark {args.benchmark}")
        data, benchmark, as_of, sectors = build_real(tickers, args.benchmark, args.start, args.end)
    else:
        _banner("synthetic, seeded, offline")
        data, benchmark, as_of, sectors = build_synthetic()

    report(data, benchmark, as_of, sectors)


if __name__ == "__main__":
    main()
