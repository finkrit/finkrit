# finagent/report/performance.py
"""
Structured performance output and its deterministic composer -- the performance
analogue of the risk report trio (metric.py + report.py + composer.py), kept in
one domain-scoped module.

Same shape and contract as the risk side:
  - every metric field is Optional and defaults to None, so a report is filled
    selectively per the requested metric set.
  - the composer fetches PortfolioData ONCE and calls the pre-fetched
    finkritintel bindings against that shared data.
  - resilient by design: a metric that cannot be computed is recorded in
    ``errors`` and left None rather than failing the whole report.

Portfolio returns are always simple, so there is no return-convention here;
``basis`` (buy-and-hold vs constant-mix) is the axis that decides which
portfolio the numbers describe, so it is recorded in the parameters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Callable

from finkritintel.integration.finkritq import (
    PORTFOLIO_ANNUALIZED_RETURN_BINDING,
    PORTFOLIO_CALMAR_RATIO_BINDING,
    PORTFOLIO_SHARPE_RATIO_BINDING,
    PORTFOLIO_SORTINO_RATIO_BINDING,
    PORTFOLIO_TOTAL_RETURN_BINDING,
)
from finkritq.data import DataRegistry
from finkritq.datatype import WeightingBasis
from finkritq.portfolio import Portfolio, PortfolioData


class PerformanceMetric(Enum):
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"


# What a PM glances at first: how much it made (total + annualized) and whether
# the return justified the risk (Sharpe). Sortino/Calmar are the fuller picture.
CORE: frozenset[PerformanceMetric] = frozenset(
    {
        PerformanceMetric.TOTAL_RETURN,
        PerformanceMetric.ANNUALIZED_RETURN,
        PerformanceMetric.SHARPE_RATIO,
    }
)

ALL: frozenset[PerformanceMetric] = frozenset(PerformanceMetric)


def resolve_metrics(
    metrics: frozenset[PerformanceMetric] | set[PerformanceMetric] | str,
) -> frozenset[PerformanceMetric]:
    """Accept the string aliases 'core'/'all' or an explicit metric set."""
    if isinstance(metrics, str):
        key = metrics.lower()
        if key == "core":
            return CORE
        if key == "all":
            return ALL
        raise ValueError(
            f"Unknown metric selector '{metrics}'. Use 'core', 'all', or a set of PerformanceMetric."
        )
    return frozenset(metrics)


@dataclass(frozen=True, slots=True, kw_only=True)
class PerformanceParameters:
    """Everything needed to label and reproduce the numbers on a dashboard."""

    as_of: date
    lookback_start: date | None = None
    lookback_end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    risk_free_rate: float = 0.0        # labels Sharpe/Sortino
    target: float = 0.0                # minimum acceptable return, for Sortino
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioPerformanceReport:
    portfolio_id: str
    params: PerformanceParameters

    total_return: float | None = None
    annualized_return: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None

    # Metric name -> reason, for metrics requested but not computable. Keeps a
    # report partial rather than failing the whole thing.
    errors: dict[str, str] = field(default_factory=dict)


def compose_portfolio_performance_report(
    portfolio: Portfolio,
    registry: DataRegistry,
    metrics: frozenset[PerformanceMetric] | set[PerformanceMetric] | str = "core",
    *,
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
    risk_free_rate: float = 0.0,
    target: float = 0.0,
    periods_per_year: int = 252,
    start: date | None = None,
    end: date | None = None,
    interval: str = "1d",
) -> PortfolioPerformanceReport:
    selected = set(resolve_metrics(metrics))
    errors: dict[str, str] = {}

    # Fetch once. If the portfolio itself can't be priced, no metric is
    # computable -- let that raise.
    data = PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval=interval)

    params = PerformanceParameters(
        as_of=date.today(),
        lookback_start=start,
        lookback_end=end,
        interval=interval,
        basis=basis,
        risk_free_rate=risk_free_rate,
        target=target,
        periods_per_year=periods_per_year,
    )

    # Each entry: PerformanceMetric -> (report_field_name, zero-arg compute).
    computers: dict[PerformanceMetric, tuple[str, Callable[[], Any]]] = {
        PerformanceMetric.TOTAL_RETURN: (
            "total_return",
            lambda: PORTFOLIO_TOTAL_RETURN_BINDING.execute(data, basis=basis),
        ),
        PerformanceMetric.ANNUALIZED_RETURN: (
            "annualized_return",
            lambda: PORTFOLIO_ANNUALIZED_RETURN_BINDING.execute(
                data, basis=basis, periods_per_year=periods_per_year
            ),
        ),
        PerformanceMetric.SHARPE_RATIO: (
            "sharpe_ratio",
            lambda: PORTFOLIO_SHARPE_RATIO_BINDING.execute(
                data, basis=basis, risk_free_rate=risk_free_rate, periods_per_year=periods_per_year
            ),
        ),
        PerformanceMetric.SORTINO_RATIO: (
            "sortino_ratio",
            lambda: PORTFOLIO_SORTINO_RATIO_BINDING.execute(
                data,
                basis=basis,
                risk_free_rate=risk_free_rate,
                target=target,
                periods_per_year=periods_per_year,
            ),
        ),
        PerformanceMetric.CALMAR_RATIO: (
            "calmar_ratio",
            lambda: PORTFOLIO_CALMAR_RATIO_BINDING.execute(
                data, basis=basis, periods_per_year=periods_per_year
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

    return PortfolioPerformanceReport(
        portfolio_id=portfolio.id, params=params, errors=errors, **values
    )
