# finagent/report/composer.py
"""
Deterministic portfolio risk report -- no LLM, no API key.

Fetches PortfolioData (and the benchmark) ONCE, then calls the pre-fetched
finkritintel bindings against that shared data. This is why both binding
variants exist: the *live* bindings fetch per-call (ad-hoc LLM tool use),
the *pre-fetched* bindings take data in (fetch-once report composer).

Resilient by design: a metric that can't be computed (no benchmark, bad
data) records into report.errors and leaves its field None, rather than
failing the whole report -- a dashboard needs partial success.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

import numpy as np

from finkritintel.integration.finkritq import (
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
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import MarketIndex, PriceHistory
from finkritq.portfolio import Portfolio, PortfolioData

from finagent.report.metric import RiskMetric, resolve_metrics
from finagent.report.report import DrawdownSummary, PortfolioRiskReport, RiskParameters

DEFAULT_BENCHMARK: Asset = MarketIndex.SP500.as_asset()


def _drawdown_summary(pd: PortfolioData) -> DrawdownSummary:
    arr = np.asarray(PORTFOLIO_DRAWDOWN_BINDING.execute(pd), dtype=float)
    if arr.size == 0:
        return DrawdownSummary(max_drawdown=0.0, current_drawdown=0.0, periods=0)

    trough_idx = int(arr.argmin())
    dates = pd.dates  # datetime64 array aligned to the drawdown series
    trough_date = None
    if trough_idx < len(dates):
        # np.datetime64 -> python date
        trough_date = np.datetime64(dates[trough_idx], "D").astype("datetime64[D]").astype(date)

    return DrawdownSummary(
        max_drawdown=float(arr.min()),
        current_drawdown=float(arr[-1]),
        periods=int(arr.size),
        trough_date=trough_date,
    )


def _contribution_map(result: Any, portfolio: Portfolio) -> dict[str, float]:
    values = np.asarray(result, dtype=float)
    return {asset.ticker: float(v) for asset, v in zip(portfolio.assets, values)}


def compose_portfolio_risk_report(
    portfolio: Portfolio,
    registry: DataRegistry,
    metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
    *,
    benchmark: Asset | None = None,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> PortfolioRiskReport:
    selected = set(resolve_metrics(metrics))
    benchmark = benchmark or DEFAULT_BENCHMARK
    errors: dict[str, str] = {}

    # Fetch once. If the portfolio itself can't be priced, no metric is
    # computable -- let that raise. The benchmark fetch only affects beta,
    # so it's isolated: a failure nulls beta, not the whole report.
    data = PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval=interval)

    benchmark_history: PriceHistory | None = None
    if RiskMetric.BETA in selected:
        try:
            benchmark_history = registry.history(benchmark, start=start, end=end, interval=interval)
        except Exception as exc:  # noqa: BLE001
            errors[RiskMetric.BETA.value] = f"{type(exc).__name__}: {exc}"
            selected.discard(RiskMetric.BETA)

    params = RiskParameters(
        as_of=date.today(),
        lookback_start=start,
        lookback_end=end,
        interval=interval,
        benchmark_ticker=benchmark.ticker if benchmark_history is not None else None,
    )

    # Each entry: RiskMetric -> (report_field_name, zero-arg compute).
    computers: dict[RiskMetric, tuple[str, Callable[[], Any]]] = {
        RiskMetric.VOLATILITY: ("volatility", lambda: PORTFOLIO_VOLATILITY_BINDING.execute(data)),
        RiskMetric.VARIANCE: ("variance", lambda: PORTFOLIO_VARIANCE_BINDING.execute(data)),
        RiskMetric.SEMIVARIANCE: ("semivariance", lambda: PORTFOLIO_SEMIVARIANCE_BINDING.execute(data)),
        RiskMetric.DOWNSIDE_DEVIATION: (
            "downside_deviation",
            lambda: PORTFOLIO_DOWNSIDE_DEVIATION_BINDING.execute(data),
        ),
        RiskMetric.VALUE_AT_RISK: (
            "value_at_risk",
            lambda: PORTFOLIO_VALUE_AT_RISK_BINDING.execute(
                data, method=params.var_method, confidence=params.confidence
            ),
        ),
        RiskMetric.CONDITIONAL_VALUE_AT_RISK: (
            "conditional_value_at_risk",
            lambda: PORTFOLIO_CONDITIONAL_VALUE_AT_RISK_BINDING.execute(
                data, method=params.var_method, confidence=params.confidence
            ),
        ),
        RiskMetric.BETA: ("beta", lambda: PORTFOLIO_BETA_BINDING.execute(data, benchmark_history)),
        RiskMetric.MAX_DRAWDOWN: (
            "max_drawdown",
            lambda: PORTFOLIO_MAXIMUM_DRAWDOWN_BINDING.execute(data),
        ),
        RiskMetric.DRAWDOWN: ("drawdown", lambda: _drawdown_summary(data)),
        RiskMetric.MARGINAL_CONTRIBUTION: (
            "marginal_contributions",
            lambda: _contribution_map(
                PORTFOLIO_MARGINAL_CONTRIBUTION_TO_RISK_BINDING.execute(data), portfolio
            ),
        ),
        RiskMetric.COMPONENT_CONTRIBUTION: (
            "component_contributions",
            lambda: _contribution_map(
                PORTFOLIO_COMPONENT_CONTRIBUTION_TO_RISK_BINDING.execute(data), portfolio
            ),
        ),
    }

    values: dict[str, Any] = {}
    for metric in selected:
        field_name, compute = computers[metric]
        try:
            values[field_name] = compute()
        except Exception as exc:  # noqa: BLE001 -- resilience is the point; recorded, not swallowed
            errors[metric.value] = f"{type(exc).__name__}: {exc}"

    return PortfolioRiskReport(portfolio_id=portfolio.id, params=params, errors=errors, **values)
