# finkritintel/integration/finkritq/risk_live.py
"""
The two multi-metric risk tools: one call, many metrics, many holdings.

Both return plain JSON-shaped dicts rather than domain objects, because their
consumer is a model reading a tool result. Both are resilient the way the
deterministic report composer is: a metric that cannot be computed records its
reason and the rest of the answer still arrives.

Why omitting ``metrics`` computes everything rather than a curated subset.
Three options were weighed, and the deciding question was which is safest to be
wrong about, since a small model's handling of enum arrays is not yet measured:

  - default to a curated few: a model that fumbles the array gets metrics that
    exclude what was asked, and narrates the wrong one as if it were right. A
    confidently wrong number is the worst failure this stack has.
  - require the argument: no wrong answers, but a model that cannot build the
    array gets nothing at all, which is the property that makes a small local
    model usable in the first place.
  - default to everything: a fumble returns a superset of what was asked.
    Wasteful, never wrong.

The third is chosen. Note where its cost lands: only on the path where the
model already failed to specify. Specify, and the result is small. The
expensive case is the recovery case, which is the right place for expense.

Two consequences that follow from that choice and are load bearing, not
cosmetic: the holdings cap below (every metric across hundreds of holdings is
thousands of numbers), and the ``computed``/``available`` keys on every result
(a model that wanted semivariance can see it is absent and ask again, rather
than mistaking an incomplete answer for a complete one).
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Callable

import numpy as np

from finkritq.anal.risk.beta import beta_asset
from finkritq.anal.risk.conditionalvalueatrisk import conditional_value_at_risk_asset
from finkritq.anal.risk.downside_deviation import downside_deviation_asset
from finkritq.anal.risk.drawdown import maximum_drawdown_asset
from finkritq.anal.risk.semivariance import semivariance_asset
from finkritq.anal.risk.valueatrisk import value_at_risk_asset
from finkritq.anal.risk.variance import variance_asset
from finkritq.anal.risk.volatility import volatility_asset
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import PORTFOLIO_ONLY_METRICS, PriceHistory, RiskMetric
from finkritq.portfolio import Portfolio, PortfolioData

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.risk import ASSET_RISK, PORTFOLIO_RISK

from .portfolio import (
    PORTFOLIO_BETA_BINDING,
    PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING,
    PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING,
    PORTFOLIO_DOWNSIDE_DEVIATION_BINDING,
    PORTFOLIO_DRAWDOWN_BINDING,
    PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING,
    PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING,
    PORTFOLIO_SEMIVARIANCE_BINDING,
    PORTFOLIO_VALUE_AT_RISK_BINDING,
    PORTFOLIO_VARIANCE_BINDING,
    PORTFOLIO_VOLATILITY_BINDING,
)
from .risk_schema_live import AssetRiskLiveInput, PortfolioRiskLiveInput

# How many holdings one asset_risk call will cover. A book of five hundred
# names against every metric is thousands of numbers, which is neither useful
# to read nor safe to hand a small model. Truncation is always reported, never
# silent: a cut list that looks complete would read as "these are all your
# holdings" when it is not.
MAX_ASSETS_PER_CALL = 25

# Significant figures, not decimal places. A volatility of 0.284114 rendered as
# a percentage to two decimals is 28.41%; round the ratio to three decimals
# first and it renders 28.40% while the dashboard, formatting the unrounded
# float, still says 28.41%. Fixed decimals also flatten small values, turning a
# 95% VaR of -0.0287 into -0.029. Significant figures are correct at every
# magnitude.
SIGNIFICANT_FIGURES = 6

PORTFOLIO_METRICS: tuple[RiskMetric, ...] = tuple(RiskMetric)

# Derived, never hand listed, so a metric added to the vocabulary cannot be
# silently missing here. Two exclusions:
#   - PORTFOLIO_ONLY_METRICS (the contribution pair) decompose a portfolio's
#     risk across its holdings, and one asset has nothing to decompose. That
#     fact lives in finkritq.datatype next to the enum.
#   - raw DRAWDOWN is a full series, one value per trading day. Worth having at
#     portfolio scope where it is summarized to a few numbers, meaningless as a
#     per holding array, and max_drawdown already carries the figure anyone
#     asks for.
ASSET_METRICS: tuple[RiskMetric, ...] = tuple(
    metric
    for metric in RiskMetric
    if metric not in PORTFOLIO_ONLY_METRICS and metric is not RiskMetric.DRAWDOWN
)


# What each number means, sent with every result.
#
# Bare floats leave a model to infer units, and a small one infers confidently
# and wrongly. Observed on a 14b reading these exact tools: value_at_risk, which
# is a fraction, reported as "$204.77" per holding and "$1,014" for the
# portfolio, figures that would need position values the model never received.
# The same run reported every beta as "over past 1 day interval", reading the
# sampling frequency as the lookback.
#
# Same principle as the computed/available keys: never leave a gap, because a
# model fills gaps rather than asking.
METRIC_UNITS: dict[RiskMetric, str] = {
    RiskMetric.VOLATILITY: "annualized fraction of value, 0.25 means 25%",
    RiskMetric.VARIANCE: "annualized fraction squared",
    RiskMetric.SEMIVARIANCE: "annualized fraction squared, downside only",
    RiskMetric.DOWNSIDE_DEVIATION: "annualized fraction of value, downside only",
    RiskMetric.VALUE_AT_RISK: "fraction of value lost, 95% confidence, one period, not a currency amount",
    RiskMetric.CONDITIONAL_VALUE_AT_RISK: "fraction of value lost beyond the 95% threshold, not a currency amount",
    RiskMetric.BETA: "ratio to the benchmark, 1.0 moves with it, unitless",
    RiskMetric.MAX_DRAWDOWN: "worst peak to trough fall as a negative fraction",
    RiskMetric.DRAWDOWN: "fractions, negative, summarized rather than the full series",
    RiskMetric.MARGINAL_CONTRIBUTION: "per holding, annualized fraction of value",
    RiskMetric.COMPONENT_CONTRIBUTION: "per holding, annualized fraction of value, sums to portfolio volatility",
}

# finkritq resolves these internally (end defaults to today, start to a year
# before), so the caller never sees them unless we resolve them here. The risk
# instructions ask the model to state the lookback it computed over, which it
# cannot do if we never send one.
DEFAULT_LOOKBACK_DAYS = 365


def _window(start: date | None, end: date | None, interval: str) -> dict[str, Any]:
    """The lookback actually used, spelled out.

    ``interval`` is how often the series is sampled, not how far back it
    reaches. Sent under a name that cannot be read as the window, next to the
    window, because reading one as the other is what produced "beta over past
    1 day interval".
    """
    resolved_end = end or date.today()
    resolved_start = start or resolved_end - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    return {
        "start": resolved_start.isoformat(),
        "end": resolved_end.isoformat(),
        "sampling": interval,
        "description": (
            f"{(resolved_end - resolved_start).days} calendar days of history, "
            f"sampled every {interval}"
        ),
    }


def _units(selected: list[RiskMetric]) -> dict[str, str]:
    return {metric.value: METRIC_UNITS[metric] for metric in selected}


def _round(value: Any) -> Any:
    """``value`` at SIGNIFICANT_FIGURES, leaving anything non numeric alone."""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating)):
        return value
    number = float(value)
    if number == 0.0 or not math.isfinite(number):
        return number
    exponent = math.floor(math.log10(abs(number)))
    return round(number, SIGNIFICANT_FIGURES - 1 - exponent)


def _select(
    metrics: tuple[RiskMetric, ...] | None, allowed: tuple[RiskMetric, ...]
) -> list[RiskMetric]:
    """Requested metrics narrowed to the ones this scope offers.

    None means all of them. An unknown or out of scope metric is dropped rather
    than raised on, because the result names what it computed and what was
    available, which tells the model more than an exception would.
    """
    if metrics is None:
        return list(allowed)
    wanted = set(metrics)
    return [metric for metric in allowed if metric in wanted]


def _drawdown_summary(series: Any) -> dict[str, Any]:
    # Four numbers instead of one per trading day. Mirrors what the dashboard's
    # report composer does with the same series.
    arr = np.asarray(series, dtype=float)
    if arr.size == 0:
        return {"max_drawdown": 0.0, "current_drawdown": 0.0, "periods": 0}
    return {
        "max_drawdown": _round(arr.min()),
        "current_drawdown": _round(arr[-1]),
        "periods": int(arr.size),
    }


def _contribution_map(result: Any, portfolio: Portfolio) -> dict[str, float]:
    values = np.asarray(result, dtype=float)
    return {asset.ticker: _round(v) for asset, v in zip(portfolio.assets, values)}


def portfolio_risk_live(
    portfolio: Portfolio,
    registry: DataRegistry,
    benchmark: Asset,
    metrics: tuple[RiskMetric, ...] | None = None,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> dict[str, Any]:
    selected = _select(metrics, PORTFOLIO_METRICS)
    errors: dict[str, str] = {}

    # Fetched once for every metric. If the portfolio itself cannot be priced
    # no metric is computable, so that is left to raise.
    data = PortfolioData.from_registry(
        portfolio, registry, start=start, end=end, interval=interval
    )

    # The benchmark fetch only affects beta, so a failure nulls beta rather
    # than the whole answer.
    benchmark_history: PriceHistory | None = None
    if RiskMetric.BETA in selected:
        try:
            benchmark_history = registry.history(
                benchmark, start=start, end=end, interval=interval
            )
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            errors[RiskMetric.BETA.value] = f"{type(exc).__name__}: {exc}"
            selected.remove(RiskMetric.BETA)

    computers: dict[RiskMetric, Callable[[], Any]] = {
        RiskMetric.VOLATILITY: lambda: PORTFOLIO_VOLATILITY_BINDING.execute(data),
        RiskMetric.VARIANCE: lambda: PORTFOLIO_VARIANCE_BINDING.execute(data),
        RiskMetric.SEMIVARIANCE: lambda: PORTFOLIO_SEMIVARIANCE_BINDING.execute(data),
        RiskMetric.DOWNSIDE_DEVIATION: lambda: PORTFOLIO_DOWNSIDE_DEVIATION_BINDING.execute(data),
        RiskMetric.VALUE_AT_RISK: lambda: PORTFOLIO_VALUE_AT_RISK_BINDING.execute(data),
        RiskMetric.CONDITIONAL_VALUE_AT_RISK: lambda: (
            PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(data)
        ),
        RiskMetric.BETA: lambda: PORTFOLIO_BETA_BINDING.execute(data, benchmark_history),
        RiskMetric.MAX_DRAWDOWN: lambda: PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING.execute(data),
        RiskMetric.DRAWDOWN: lambda: _drawdown_summary(PORTFOLIO_DRAWDOWN_BINDING.execute(data)),
        RiskMetric.MARGINAL_CONTRIBUTION: lambda: _contribution_map(
            PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING.execute(data), portfolio
        ),
        RiskMetric.COMPONENT_CONTRIBUTION: lambda: _contribution_map(
            PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING.execute(data), portfolio
        ),
    }

    values: dict[str, Any] = {}
    for metric in selected:
        try:
            values[metric.value] = _round(computers[metric]())
        except Exception as exc:  # noqa: BLE001 - resilience is the point
            errors[metric.value] = f"{type(exc).__name__}: {exc}"

    return {
        "portfolio_id": portfolio.id,
        "metrics": values,
        "computed": sorted(values),
        "available": sorted(m.value for m in PORTFOLIO_METRICS if m.value not in values),
        "errors": errors,
        "benchmark_ticker": benchmark.ticker if benchmark_history is not None else None,
        "window": _window(start, end, interval),
        "units": _units(selected),
    }


def asset_risk_live(
    portfolio: Portfolio,
    registry: DataRegistry,
    benchmark: Asset,
    assets: tuple[Asset, ...] | None = None,
    metrics: tuple[RiskMetric, ...] | None = None,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> dict[str, Any]:
    # None means the whole portfolio. This is the case the tool exists for: the
    # model holds an opaque portfolio id and cannot name a single ticker, so
    # "the betas of my holdings" has to resolve holdings on this side.
    chosen = tuple(assets) if assets else tuple(portfolio.assets)
    omitted = max(0, len(chosen) - MAX_ASSETS_PER_CALL)
    chosen = chosen[:MAX_ASSETS_PER_CALL]

    selected = _select(metrics, ASSET_METRICS)
    errors: dict[str, str] = {}

    def computers(asset: Asset) -> dict[RiskMetric, Callable[[], Any]]:
        # Each of these fetches the asset's history through the registry, which
        # memoizes, so N metrics for one asset is one download and N reads.
        window = {"start": start, "end": end, "interval": interval}
        return {
            RiskMetric.VOLATILITY: lambda: volatility_asset(asset, registry, **window),
            RiskMetric.VARIANCE: lambda: variance_asset(asset, registry, **window),
            RiskMetric.SEMIVARIANCE: lambda: semivariance_asset(asset, registry, **window),
            RiskMetric.DOWNSIDE_DEVIATION: lambda: downside_deviation_asset(
                asset, registry, **window
            ),
            RiskMetric.VALUE_AT_RISK: lambda: value_at_risk_asset(asset, registry, **window),
            RiskMetric.CONDITIONAL_VALUE_AT_RISK: lambda: conditional_value_at_risk_asset(
                asset, registry, **window
            ),
            RiskMetric.BETA: lambda: beta_asset(asset, benchmark, registry, **window),
            RiskMetric.MAX_DRAWDOWN: lambda: maximum_drawdown_asset(asset, registry, **window),
        }

    holdings: dict[str, dict[str, Any]] = {}
    names: dict[str, str] = {}
    for asset in chosen:
        # The security's own name, so a model narrating the table has it in
        # hand. Left out when it is just the ticker back, which says nothing.
        # A model given a bare ticker supplies a name from memory, and one
        # observed run labelled V as "Vanguard Utilities ETF". It is Visa.
        company = getattr(asset, "company_name", None)
        if company and company != asset.ticker:
            names[asset.ticker] = company
        row: dict[str, Any] = {}
        available = computers(asset)
        for metric in selected:
            try:
                row[metric.value] = _round(available[metric]())
            except Exception as exc:  # noqa: BLE001 - one bad ticker is not the answer
                errors[f"{asset.ticker}.{metric.value}"] = f"{type(exc).__name__}: {exc}"
        holdings[asset.ticker] = row

    computed = sorted({name for row in holdings.values() for name in row})
    result: dict[str, Any] = {
        "portfolio_id": portfolio.id,
        "holdings": holdings,
        "names": names,
        "computed": computed,
        "available": sorted(m.value for m in ASSET_METRICS if m.value not in computed),
        "errors": errors,
        "benchmark_ticker": benchmark.ticker if RiskMetric.BETA in selected else None,
        "window": _window(start, end, interval),
        "units": _units(selected),
    }
    if omitted:
        # Named rather than dropped. A truncated list that looks whole would
        # read as the entire portfolio.
        result["omitted_holdings"] = omitted
        result["note"] = (
            f"Showing the first {MAX_ASSETS_PER_CALL} holdings, {omitted} not shown. "
            f"Pass tickers to choose which."
        )
    return result


PORTFOLIO_RISK_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_RISK,
    input_schema=PortfolioRiskLiveInput,
    output_schema=dict,
    implementation=portfolio_risk_live,
)

ASSET_RISK_LIVE_BINDING = ToolBinding(
    contract=ASSET_RISK,
    input_schema=AssetRiskLiveInput,
    output_schema=dict,
    implementation=asset_risk_live,
)
