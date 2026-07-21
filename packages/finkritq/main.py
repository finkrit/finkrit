# finkrit/packages/finkritq/main.py
"""
Runnable example: build a fake portfolio (no network) and run every finkritq
analytic pillar over it, risk, performance, and optimization.

    python -m finkritq

The data is synthetic and seeded, so the numbers are reproducible. Asset returns
are driven by a shared market factor plus idiosyncratic noise, so beta and the
benchmark-relative metrics are meaningful.
"""
from __future__ import annotations

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
from finkritq.datatype import Currency, Exchange, PriceHistory
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

_N = 120        # return intervals -> 121 price observations
_AS_OF = date(2024, 5, 1)   # reference date for holding-period / wash-sale checks


# ---------------------------------------------------------------------------
# Synthetic, seeded market (no network)
# ---------------------------------------------------------------------------

def _dates(n: int) -> np.ndarray:
    base = np.datetime64("2024-01-02", "D")
    return np.array([base + np.timedelta64(i, "D") for i in range(n)], dtype="datetime64[D]")


def _history(close: np.ndarray) -> PriceHistory:
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    return PriceHistory(
        dates=_dates(n),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=np.ones(n, dtype=np.int64),
    )


def _stock(ticker: str) -> Stock:
    return Stock(ticker=ticker, currency=Currency.USD, exchange=Exchange.NASDAQ, company_name=f"{ticker} Corp")


def _position(stock: Stock, quantity: str, position_id: str, lot_id: str) -> Position:
    # Two lots per position so the tax features have something to chew on: an old
    # cheap long-term lot (a gain) and a recent expensive lot (a likely loss that
    # is harvestable, and the one HIFO sells first).
    half = Decimal(quantity) / 2
    lots = (
        TaxLot(id=f"{lot_id}-old", quantity=half, cost_per_share=Decimal("85"), acquired=date(2022, 1, 3)),
        TaxLot(id=f"{lot_id}-new", quantity=half, cost_per_share=Decimal("130"), acquired=date(2024, 3, 15)),
    )
    return Position(id=position_id, asset=stock, lots=lots)


def _build() -> tuple[PortfolioData, PriceHistory]:
    rng = np.random.default_rng(0)
    market = rng.normal(0.0009, 0.008, _N)  # market factor per-period returns

    def series(beta: float, drift: float, idio: float) -> np.ndarray:
        r = drift + beta * market + rng.normal(0.0, idio, _N)
        return 100.0 * np.exp(np.cumsum(np.insert(r, 0, 0.0)))

    aaa, bbb, ccc = _stock("AAA"), _stock("BBB"), _stock("CCC")
    positions = [
        _position(aaa, "100", "p-aaa", "l-aaa"),
        _position(bbb, "50", "p-bbb", "l-bbb"),
        _position(ccc, "75", "p-ccc", "l-ccc"),
    ]
    portfolio = Portfolio(id="demo", name="Demo Portfolio", positions=positions)

    histories = {
        aaa: _history(series(beta=1.2, drift=0.0004, idio=0.008)),
        bbb: _history(series(beta=0.8, drift=0.0006, idio=0.010)),
        ccc: _history(series(beta=1.0, drift=0.0005, idio=0.006)),
    }
    data = PortfolioData(portfolio=portfolio, _histories=histories)

    benchmark = _history(1000.0 * np.exp(np.cumsum(np.insert(market, 0, 0.0))))
    return data, benchmark


# ---------------------------------------------------------------------------
# Reporting
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


def main() -> None:
    data, benchmark = _build()

    _header("PORTFOLIO")
    print(f"  {data.portfolio.name}: {data.portfolio.position_count} positions, "
          f"{len(data)} observations")
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
    assets = data.assets
    model = {assets[0]: 0.34, assets[1]: 0.33, assets[2]: 0.33}
    print(f"  total drift from model: {total_drift(data, model) * 100:.2f}%")
    print("  rebalance trades (drift-ranked):")
    for trade in rebalance_to_model(data, model):
        side = "BUY " if trade.is_buy else "SELL"
        print(f"    {side} {trade.asset.ticker:<5} ${abs(trade.trade_value):>10,.0f}"
              f"   (drift {trade.drift * 100:+.1f}%)")

    prices = {asset: Decimal(str(round(price, 2))) for asset, price in data.latest_prices.items()}
    report = harvest_candidates(data.portfolio, prices, _AS_OF)
    print(f"  tax-loss harvest: ${report.total_harvestable_loss:,.0f} harvestable"
          f"  (ST ${report.short_term_loss:,.0f} / LT ${report.long_term_loss:,.0f})")
    for candidate in report.candidates:
        term = "LT" if candidate.is_long_term else "ST"
        print(f"    {candidate.asset.ticker:<5} lot {candidate.lot.id:<10}"
              f" loss ${candidate.unrealized_loss:>8,.0f}  ({term})")

    first = data.portfolio.positions[0]
    sale = select_lots_to_sell(
        first, first.quantity / 2, prices[first.asset], _AS_OF, method=LotSaleMethod.HIFO
    )
    print(f"  HIFO sell {sale.quantity_sold} {first.asset.ticker}:"
          f" realized ${sale.realized_gain:,.0f}"
          f"  (ST ${sale.short_term_gain:,.0f} / LT ${sale.long_term_gain:,.0f})")

    plan = invest_cashflow(data, model, cash=50_000.0, set_aside=5_000.0)
    print(f"  cash deposit $50,000 (hold back $5,000) -> deploy ${plan.cash_deployed:,.0f}:")
    for trade in plan.trades:
        print(f"    BUY  {trade.asset.ticker:<5} ${trade.trade_value:>10,.0f}")

    budgeted = tax_aware_rebalance(data, model, prices, _AS_OF, gain_budget=200.0)
    deferred = f", deferred {[a.ticker for a in budgeted.deferred]}" if budgeted.deferred else ""
    print(f"  tax-budgeted rebalance (gain budget $200):"
          f" realized ${budgeted.realized_gain:,.0f}, harvested ${budgeted.harvested_loss:,.0f}{deferred}")

    _header("RETURNS WITH FLOWS (TWR vs MWR)")
    actual = np.asarray(data.value, dtype=np.float64)
    flows = np.zeros(len(actual))
    mid = len(actual) // 2
    flows[mid] = 20_000.0
    actual_with_flow = actual.copy()
    actual_with_flow[mid:] += 20_000.0
    print("  with a $20,000 contribution midway (annualized):")
    _row("time-weighted (manager skill)",
         time_weighted_return(actual_with_flow, flows, annualized=True), pct=True)
    _row("money-weighted / IRR (client)",
         money_weighted_return(actual_with_flow, flows, annualized=True), pct=True)

    _header("ATTRIBUTION (allocation vs selection)")
    portfolio_returns = {asset: total_return_from_prices(data[asset].close) for asset in data.assets}
    benchmark_return = total_return_from_prices(benchmark.close)
    benchmark_returns = {asset: benchmark_return for asset in data.assets}
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
    sectors = {"AAA": "Technology", "BBB": "Financials", "CCC": "Technology"}
    exposure = exposure_by_group(data.weights, lambda asset: sectors[asset.ticker])
    print("  sector exposure:")
    for sector, weight in sorted(exposure.items(), key=lambda kv: kv[1], reverse=True):
        print(f"    {sector:<14} {weight * 100:6.2f}%")
    print()


if __name__ == "__main__":
    main()
