from __future__ import annotations

from finkritq.data import DataRegistry
from finkritq.optimize import maximum_sharpe_portfolio, minimum_variance_portfolio
from finkritq.portfolio import Portfolio, PortfolioData

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.optimization import (
    OPTIMIZE_MAXIMUM_SHARPE,
    OPTIMIZE_MINIMUM_VARIANCE,
)
from finkritintel.integration.finkritq.optimization_schema_live import (
    MaximumSharpeLiveInput,
    MinimumVarianceLiveInput,
)


def _fetch(portfolio: Portfolio, registry: DataRegistry, start, end, interval) -> PortfolioData:
    return PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval=interval)


# Live wrappers fetch PortfolioData, then delegate to the finkritq optimizer.
# Each returns a dict[Asset, float] of optimal weights, reshaped to ticker->weight
# by the agent-edge output adapter.


def _minimum_variance_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d", long_only=True,
) -> dict:
    return minimum_variance_portfolio(_fetch(portfolio, registry, start, end, interval), long_only=long_only)


def _maximum_sharpe_live(
    portfolio: Portfolio, registry: DataRegistry,
    start=None, end=None, interval="1d", risk_free_rate=0.0, long_only=True,
) -> dict:
    return maximum_sharpe_portfolio(
        _fetch(portfolio, registry, start, end, interval),
        risk_free_rate=risk_free_rate, long_only=long_only,
    )


OPTIMIZE_MINIMUM_VARIANCE_LIVE_BINDING = ToolBinding(
    contract=OPTIMIZE_MINIMUM_VARIANCE,
    input_schema=MinimumVarianceLiveInput,
    output_schema=dict,
    implementation=_minimum_variance_live,
)

OPTIMIZE_MAXIMUM_SHARPE_LIVE_BINDING = ToolBinding(
    contract=OPTIMIZE_MAXIMUM_SHARPE,
    input_schema=MaximumSharpeLiveInput,
    output_schema=dict,
    implementation=_maximum_sharpe_live,
)
