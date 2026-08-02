# finkritintel/integration/finkritq/rebalance_live.py
"""
Live binding for tax-aware rebalancing, the optimizer-to-tax composition.

The whole chain runs in code: the optimizer produces target weights from
history, spot prices come from the registry, and the tax-budgeted loop picks
lots and defers gain sells. The model chooses the objective, the budget, and
the lot method, and narrates the resulting plan. It never computes or copies a
weight, which is the point to prevent transcription error in a trade plan (worse
than one in a description).

Output is position level: per asset sell value, realized gain and its long
versus short split, and how many lots the sale touches. Lot ids and dates stay
out, matching the boundary the tax wrappers draw.
"""
from __future__ import annotations

from datetime import date

from finkritq.data import DataRegistry
from finkritq.datatype import LotSaleMethod, RebalanceSizing
from finkritq.optimize import (
    TaxRebalancePlan,
    compare_rebalance_strategies,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    tax_aware_rebalance,
)
from finkritq.portfolio import Portfolio, PortfolioData

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.rebalance import (
    PORTFOLIO_REBALANCE_COMPARE,
    PORTFOLIO_TAX_AWARE_REBALANCE,
)
from finkritintel.integration.finkritq.rebalance_schema_live import (
    RebalanceCompareLiveInput,
    TaxAwareRebalanceLiveInput,
)
# Same spot-price source and rounding as the read-only tax tools, so a plan's
# numbers agree with the gains report the model may have just shown.
from finkritintel.integration.finkritq.tax_live import _money, _ratio, spot_prices

_OBJECTIVES = ("min_variance", "max_sharpe")


def _validated(objective: str, gain_budget: float | None) -> None:
    if objective not in _OBJECTIVES:
        raise ValueError(
            f"Unknown objective {objective!r}. Use one of: {', '.join(_OBJECTIVES)}."
        )
    if gain_budget is not None and gain_budget < 0:
        raise ValueError("gain_budget must be zero or positive dollars.")


def _target_weights(
    portfolio: Portfolio, registry: DataRegistry,
    objective: str, start: date | None, end: date | None,
) -> tuple[PortfolioData, dict]:
    data = PortfolioData.from_registry(portfolio, registry, start=start, end=end, interval="1d")
    if objective == "min_variance":
        return data, minimum_variance_portfolio(data, long_only=True)
    return data, maximum_sharpe_portfolio(data, long_only=True)


def _serialize_plan(plan: TaxRebalancePlan) -> dict:
    # One plan, position level, shared verbatim between the single tool and
    # each row of the compare so the two can never drift apart in shape.
    return {
        "sells": [
            {
                "ticker": sell.asset.ticker,
                "sell_value": _money(sell.sell_value),
                # What actually executed. Equals sell_value unless partial.
                "executed_value": _money(sell.sale.proceeds),
                "realized_gain": _money(sell.realized_gain),
                "short_term_gain": _money(sell.sale.short_term_gain),
                "long_term_gain": _money(sell.sale.long_term_gain),
                "is_harvest": sell.is_harvest,
                "is_partial": sell.is_partial,
                "lots_touched": len(sell.sale.realized_lots),
            }
            for sell in plan.sells
        ],
        # Overweights whose sale would breach the budget. Deferring them is the
        # tax sensitivity dial doing its job, name them so the model can say
        # what a bigger budget would unlock.
        "deferred": [asset.ticker for asset in plan.deferred],
        "realized_gain": _money(plan.realized_gain),
        "short_term_gain": _money(plan.short_term_gain),
        "long_term_gain": _money(plan.long_term_gain),
        "harvested_loss": _money(plan.harvested_loss),
        # Overweight still held after the sells, as a fraction of portfolio
        # value. The tracking cost paid for the tax bill, 0 means every
        # overweight was sold fully to target.
        "residual_drift": _ratio(plan.residual_drift),
    }


_NOTE = (
    "Sell side only, proceeds fund the underweight buys. A proposal, "
    "not an executed trade."
)


def _portfolio_tax_aware_rebalance_live(
    portfolio: Portfolio,
    registry: DataRegistry,
    objective: str = "min_variance",
    gain_budget: float | None = None,
    method: LotSaleMethod = LotSaleMethod.HIFO,
    tolerance: float = 0.0,
    sizing: RebalanceSizing = RebalanceSizing.TO_TARGET,
    partial_fill: bool = False,
    as_of: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    _validated(objective, gain_budget)
    as_of = as_of or date.today()
    data, weights = _target_weights(portfolio, registry, objective, start, end)

    plan = tax_aware_rebalance(
        data,
        weights,
        prices=spot_prices(portfolio, registry),
        as_of=as_of,
        gain_budget=float("inf") if gain_budget is None else gain_budget,
        tolerance=tolerance,
        method=method,
        sizing=sizing,
        partial_fill=partial_fill,
    )

    return {
        "as_of": as_of.isoformat(),
        "objective": objective,
        "method": method.value,
        "sizing": sizing.value,
        "partial_fill": partial_fill,
        "gain_budget": None if gain_budget is None else _money(gain_budget),
        "target_weights": {
            asset.ticker: _ratio(weight) for asset, weight in weights.items()
        },
        **_serialize_plan(plan),
        "note": _NOTE,
    }


def _portfolio_rebalance_compare_live(
    portfolio: Portfolio,
    registry: DataRegistry,
    objective: str = "min_variance",
    gain_budget: float | None = None,
    method: LotSaleMethod = LotSaleMethod.HIFO,
    tolerance: float = 0.02,
    as_of: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    # The strategy menu is fixed in code (REBALANCE_STRATEGIES), deliberately
    # not a parameter: three named rows a customer can tell apart beat a free
    # combination surface the model would have to invent labels for.
    _validated(objective, gain_budget)
    as_of = as_of or date.today()
    data, weights = _target_weights(portfolio, registry, objective, start, end)

    plans = compare_rebalance_strategies(
        data,
        weights,
        prices=spot_prices(portfolio, registry),
        as_of=as_of,
        gain_budget=float("inf") if gain_budget is None else gain_budget,
        tolerance=tolerance,
        method=method,
    )

    return {
        "as_of": as_of.isoformat(),
        "objective": objective,
        "method": method.value,
        "tolerance": _ratio(tolerance),
        "gain_budget": None if gain_budget is None else _money(gain_budget),
        # Shared across every row, which is what makes the rows comparable.
        "target_weights": {
            asset.ticker: _ratio(weight) for asset, weight in weights.items()
        },
        "strategies": {
            name: _serialize_plan(plan) for name, plan in plans.items()
        },
        "note": _NOTE,
    }


PORTFOLIO_TAX_AWARE_REBALANCE_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_TAX_AWARE_REBALANCE,
    input_schema=TaxAwareRebalanceLiveInput,
    output_schema=dict,
    implementation=_portfolio_tax_aware_rebalance_live,
)

PORTFOLIO_REBALANCE_COMPARE_LIVE_BINDING = ToolBinding(
    contract=PORTFOLIO_REBALANCE_COMPARE,
    input_schema=RebalanceCompareLiveInput,
    output_schema=dict,
    implementation=_portfolio_rebalance_compare_live,
)
