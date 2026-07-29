# finkrit/packages/finkritq/optimize/taxrebalance.py
"""
Tax-budgeted rebalancing, the core loop of tax-managed rebalancing, and the
operation that ties together the three tax primitives (rebalance, lot selection,
harvest).

Rebalance toward the model, but obey a capital-gains budget: realize losses
freely (harvest), and realize gains only until the net realized gain hits the
budget, gain-generating sells beyond that are deferred (the "tax
sensitivity" dial). Harvested losses net against the budget, creating room for
gains. Optionally, proceeds from a harvest are reinvested into a *replacement*
security so the portfolio stays invested without tripping the wash sale on the
original name.

Sells are chosen drift-first (biggest offenders), and the lots each sell realizes
come from tax-aware lot selection (HIFO by default). Pure holdings + lots + a
price and gain budget, no org graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from finkritq.asset import Asset
from finkritq.datatype import RebalanceSizing
from finkritq.optimize.lotselection import (
    LotSaleMethod,
    SaleResult,
    select_lots_to_sell,
    select_lots_to_sell_within_gain,
)
from finkritq.optimize.rebalance import RebalanceTrade, rebalance_to_model, rebalance_to_policy
from finkritq.policy import Policy
from finkritq.portfolio import PortfolioData, Position


@dataclass(frozen=True, slots=True)
class TaxRebalanceSell:
    asset: Asset
    sell_value: float          # dollars requested by the rebalance (positive magnitude)
    sale: SaleResult           # the lots realized and their gain split
    is_harvest: bool           # realized a net loss
    # True when the budget cut this sell short of the requested dollars: the
    # sale is a prefix of the lot order that exactly exhausts the remaining
    # gain room. sale.proceeds is what actually executed, sell_value what the
    # rebalance asked for.
    is_partial: bool = False

    @property
    def realized_gain(self) -> Decimal:
        return self.sale.realized_gain


@dataclass(frozen=True, slots=True)
class TaxRebalancePlan:
    sells: list[TaxRebalanceSell]
    deferred: list[Asset]                      # gain-sells skipped to stay in budget
    realized_gain: Decimal
    short_term_gain: Decimal
    long_term_gain: Decimal
    harvested_loss: Decimal                    # positive magnitude of losses realized
    gain_budget: float
    replacement_buys: dict[Asset, float] = field(default_factory=dict)
    # Overweight still held after the plan's sells, as a fraction of portfolio
    # value. 0.0 means every overweight the plan saw was sold fully to target.
    # Band edge leaves the tolerance behind on every traded name, a deferral
    # leaves the whole drift, a partial fill leaves the unexecuted remainder.
    # This is the tracking cost a plan pays for its tax bill, which is what
    # makes two plans with different sizing comparable.
    residual_drift: float = 0.0


def _aggregate_position(portfolio_data: PortfolioData, asset: Asset) -> Position:
    # A synthetic position pooling every lot of this asset across the book, so lot
    # selection sees the whole tax-lot inventory for the name.
    lots = tuple(
        lot
        for position in portfolio_data.portfolio.positions
        if position.asset == asset
        for lot in position.lots
    )
    return Position(id=f"agg-{asset.ticker}", asset=asset, lots=lots)


def _residual_drift(
    portfolio_data: PortfolioData,
    trades: list[RebalanceTrade],
    target_weights: dict[Asset, float] | None,
    executed: list[TaxRebalanceSell],
) -> float:
    # Overweight still held after the executed sells. Targets come from the
    # caller's map where given, overlaid with each trade's own (possibly
    # policy-clamped) target, and any asset neither knows about is treated as
    # on-target so it contributes nothing rather than a made-up drift.
    total_value = float(portfolio_data.value[-1])
    current = portfolio_data.weights
    targets = dict(target_weights or {})
    targets.update({trade.asset: trade.target_weight for trade in trades})

    reduction = {sell.asset: float(sell.sale.proceeds) / total_value for sell in executed}

    residual = 0.0
    for asset in set(current) | set(targets):
        current_weight = current.get(asset, 0.0)
        target = targets.get(asset, current_weight)
        residual += max(current_weight - reduction.get(asset, 0.0) - target, 0.0)
    return residual


def _tax_budgeted_plan(
    portfolio_data: PortfolioData,
    trades: list[RebalanceTrade],
    prices: dict[Asset, Decimal],
    as_of: date,
    gain_budget: float,
    method: LotSaleMethod,
    replacements: dict[Asset, Asset] | None,
    partial_fill: bool = False,
    target_weights: dict[Asset, float] | None = None,
) -> TaxRebalancePlan:
    # Shared engine for both entry points: given proposed trades, realize the
    # sells drift-first under the gain budget (losses always, gains until the
    # budget is hit, the rest deferred), reinvesting harvest proceeds into a
    # replacement where one is mapped. Where the trades came from (a bare target
    # or a Policy) is the caller's concern.
    #
    # With partial_fill, a sell that would breach the budget is scaled down to
    # a prefix of its lot order that exactly exhausts the remaining gain room,
    # instead of being deferred whole. Deferral then only happens when not even
    # one share fits, i.e. the next lot in order is a gain lot and the room is
    # gone.
    replacements = replacements or {}
    sell_trades = [t for t in trades if not t.is_buy]  # trade_value < 0
    sells_by_priority = sorted(sell_trades, key=lambda t: abs(t.drift), reverse=True)

    budget = Decimal(str(gain_budget)) if gain_budget != float("inf") else None
    net_gain = Decimal("0")
    executed: list[TaxRebalanceSell] = []
    deferred: list[Asset] = []
    replacement_buys: dict[Asset, float] = {}
    short_term = Decimal("0")
    long_term = Decimal("0")
    harvested = Decimal("0")

    for trade in sells_by_priority:
        asset = trade.asset
        price = prices[asset]
        position = _aggregate_position(portfolio_data, asset)

        quantity = Decimal(str(abs(trade.trade_value))) / price
        quantity = min(quantity, position.quantity)
        if quantity <= 0:
            continue

        sale = select_lots_to_sell(position, quantity, price, as_of, method=method)
        gain = sale.realized_gain
        is_partial = False

        if gain > 0 and budget is not None and net_gain + gain > budget:
            if not partial_fill:
                deferred.append(asset)     # would breach the gain budget -> defer
                continue
            sale = select_lots_to_sell_within_gain(
                position, quantity, price, as_of,
                max_gain=budget - net_gain, method=method,
            )
            if sale.quantity_sold <= 0:
                deferred.append(asset)     # not even one share fits the room
                continue
            gain = sale.realized_gain
            is_partial = True

        executed.append(TaxRebalanceSell(
            asset=asset,
            sell_value=abs(trade.trade_value),
            sale=sale,
            is_harvest=gain < 0,
            is_partial=is_partial,
        ))
        net_gain += gain
        short_term += sale.short_term_gain
        long_term += sale.long_term_gain
        if gain < 0:
            harvested += -gain
            substitute = replacements.get(asset)
            if substitute is not None:
                replacement_buys[substitute] = replacement_buys.get(substitute, 0.0) + float(sale.proceeds)

    return TaxRebalancePlan(
        sells=executed,
        deferred=deferred,
        realized_gain=short_term + long_term,
        short_term_gain=short_term,
        long_term_gain=long_term,
        harvested_loss=harvested,
        gain_budget=gain_budget,
        replacement_buys=replacement_buys,
        residual_drift=_residual_drift(portfolio_data, trades, target_weights, executed),
    )


def tax_aware_rebalance(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
    prices: dict[Asset, Decimal],
    as_of: date,
    gain_budget: float = float("inf"),
    tolerance: float = 0.0,
    method: LotSaleMethod = LotSaleMethod.HIFO,
    replacements: dict[Asset, Asset] | None = None,
    sizing: RebalanceSizing = RebalanceSizing.TO_TARGET,
    partial_fill: bool = False,
) -> TaxRebalancePlan:
    """
    Rebalance toward ``target_weights`` under a ``gain_budget`` (max net realized
    capital gain in dollars, default unlimited). Losses are always realized, gains
    are realized drift-first until the net gain would exceed the budget, then
    deferred. ``replacements`` maps a harvested asset to a substitute bought with
    the proceeds.

    ``sizing`` picks the trade destination (to target, or only to the band edge,
    which needs a positive ``tolerance``). ``partial_fill`` scales a
    budget-breaching sell down to exactly exhaust the remaining gain room
    instead of deferring it whole. The two compose: sizing decides how much each
    sell asks for, partial fill decides what happens when the budget cannot
    afford the ask.
    """
    trades = rebalance_to_model(
        portfolio_data, target_weights, tolerance=tolerance, sizing=sizing
    )
    return _tax_budgeted_plan(
        portfolio_data, trades, prices, as_of, gain_budget, method, replacements,
        partial_fill=partial_fill, target_weights=target_weights,
    )


def tax_aware_rebalance_to_policy(
    portfolio_data: PortfolioData,
    policy: Policy,
    prices: dict[Asset, Decimal],
    as_of: date,
    gain_budget: float = float("inf"),
    method: LotSaleMethod = LotSaleMethod.HIFO,
    replacements: dict[Asset, Asset] | None = None,
) -> TaxRebalancePlan:
    """
    Tax-budgeted rebalance driven by a ``Policy``: the sells come from
    ``rebalance_to_policy`` (so drift bands and holding restrictions are honored,
    a DO_NOT_HOLD name is force-sold, a capped name trimmed) and are then realized
    under the ``gain_budget`` exactly as ``tax_aware_rebalance`` does. This is the
    fully honest propose step, respecting the rules AND the tax bill at once,
    rather than a bare target with a flat tolerance.
    """
    trades = rebalance_to_policy(portfolio_data, policy)
    return _tax_budgeted_plan(
        portfolio_data, trades, prices, as_of, gain_budget, method, replacements
    )


# The named strategy menu compare_rebalance_strategies runs. A fixed, legible
# set rather than a free combination surface: each name is a customer-facing
# label, and a new combination earns a row here when someone actually needs it.
REBALANCE_STRATEGIES: dict[str, tuple[RebalanceSizing, bool]] = {
    # name -> (sizing, partial_fill)
    "full": (RebalanceSizing.TO_TARGET, False),
    "band_edge": (RebalanceSizing.TO_BAND_EDGE, False),
    "partial_fill": (RebalanceSizing.TO_TARGET, True),
}


def compare_rebalance_strategies(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
    prices: dict[Asset, Decimal],
    as_of: date,
    gain_budget: float = float("inf"),
    tolerance: float = 0.02,
    method: LotSaleMethod = LotSaleMethod.HIFO,
) -> dict[str, TaxRebalancePlan]:
    """
    Run the same rebalance under every named strategy and return the plans
    keyed by strategy name, so tax cost and residual drift can be laid side by
    side. Everything else is held constant: one target, one price set, one
    budget, one lot method, which is what makes the rows an actual comparison
    rather than three different questions.

    Needs a positive ``tolerance`` because the band edge row is meaningless
    without a band. With an unlimited budget the partial fill row degenerates
    to the full row, since nothing ever breaches.
    """
    if tolerance <= 0.0:
        raise ValueError(
            "compare_rebalance_strategies needs a positive tolerance, the "
            "band_edge strategy has no meaning without a band. Use e.g. 0.02."
        )
    return {
        name: tax_aware_rebalance(
            portfolio_data, target_weights, prices, as_of,
            gain_budget=gain_budget, tolerance=tolerance, method=method,
            sizing=sizing, partial_fill=partial_fill,
        )
        for name, (sizing, partial_fill) in REBALANCE_STRATEGIES.items()
    }
