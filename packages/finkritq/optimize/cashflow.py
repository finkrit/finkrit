# finkrit/packages/finkritq/optimize/cashflow.py
"""
Cash-flow rebalancing, the "put new deposits to work" / "raise cash"
workflow, the most common daily trading operation.

A deposit is invested toward the model by buying the *underweights* first, a
withdrawal is funded by trimming the *overweights* first. Neither does a full
rebalance (that churns the whole book and realizes needless gains), they only
move the cash, nudging the portfolio toward the model as a side effect. A
``set_aside`` reserve can be held back from a deposit (a cash-bucket reserve).

Pure weights and dollars, the lots a sell
touches come from tax-aware lot selection.
"""
from __future__ import annotations

from dataclasses import dataclass

from finkritq.asset import Asset
from finkritq.optimize.rebalance import RebalanceTrade
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class CashFlowPlan:
    trades: list[RebalanceTrade]
    cash_deployed: float    # dollars actually bought (deposit) or raised (withdrawal)
    cash_remaining: float   # uninvested leftover on a deposit (0 on a withdrawal)
    set_aside: float


def _trade(asset: Asset, current_value: float, current_weight: float,
           target_weight: float, trade_value: float) -> RebalanceTrade:
    return RebalanceTrade(
        asset=asset,
        current_weight=current_weight,
        target_weight=target_weight,
        drift=current_weight - target_weight,
        trade_value=trade_value,
    )


def invest_cashflow(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
    cash: float,
    set_aside: float = 0.0,
) -> CashFlowPlan:
    """
    Deploy ``cash`` toward the model. ``cash > 0`` is a deposit (buy underweights),
    ``cash < 0`` is a withdrawal (sell overweights to raise ``-cash``).
    ``set_aside`` (deposits only) is held back as cash.

    A deposit fills each asset's dollar shortfall-to-target, pro-rated if the cash
    is not enough to reach the model, any surplus beyond full funding is returned
    as ``cash_remaining``. A withdrawal raises the needed cash from over-target
    positions pro-rata, falling back to trimming all holdings by weight if the
    overweights alone cannot cover it.
    """
    current_value = float(portfolio_data.value[-1])
    weights = portfolio_data.weights
    current_dollars = {asset: w * current_value for asset, w in weights.items()}
    assets = set(current_dollars) | set(target_weights)

    if cash >= 0.0:
        return _invest_deposit(portfolio_data, target_weights, cash, set_aside,
                               current_value, weights, current_dollars, assets)
    return _fund_withdrawal(portfolio_data, target_weights, -cash,
                            current_value, weights, current_dollars, assets)


def _invest_deposit(portfolio_data, target_weights, cash, set_aside,
                    current_value, weights, current_dollars, assets) -> CashFlowPlan:
    available = max(cash - set_aside, 0.0)
    new_total = current_value + available  # invested base after the deposit

    shortfalls = {}
    for asset in assets:
        target_dollar = target_weights.get(asset, 0.0) * new_total
        shortfall = target_dollar - current_dollars.get(asset, 0.0)
        if shortfall > 0.0:
            shortfalls[asset] = shortfall

    total_short = sum(shortfalls.values())
    trades: list[RebalanceTrade] = []
    if total_short > 0.0 and available > 0.0:
        # Fill shortfalls fully if the cash covers them, else pro-rata.
        scale = min(1.0, available / total_short)
        for asset, shortfall in shortfalls.items():
            buy = shortfall * scale
            trades.append(_trade(asset, current_value, weights.get(asset, 0.0),
                                 target_weights.get(asset, 0.0), buy))

    deployed = min(available, total_short)
    trades.sort(key=lambda t: t.trade_value, reverse=True)  # biggest buys first
    return CashFlowPlan(
        trades=trades,
        cash_deployed=deployed,
        cash_remaining=cash - deployed,   # set_aside + any unfundable remainder
        set_aside=set_aside,
    )


def _fund_withdrawal(portfolio_data, target_weights, need,
                     current_value, weights, current_dollars, assets) -> CashFlowPlan:
    new_total = current_value - need
    surpluses = {}
    for asset in assets:
        target_dollar = target_weights.get(asset, 0.0) * new_total
        surplus = current_dollars.get(asset, 0.0) - target_dollar
        if surplus > 0.0:
            surpluses[asset] = surplus

    total_surplus = sum(surpluses.values())
    sells: dict[Asset, float] = {}
    if total_surplus >= need:
        scale = need / total_surplus
        for asset, surplus in surpluses.items():
            sells[asset] = surplus * scale
    else:
        # Overweights cannot cover it: trim them fully, raise the rest pro-rata
        # across all holdings by current weight.
        for asset, surplus in surpluses.items():
            sells[asset] = surplus
        remaining = need - total_surplus
        for asset, dollars in current_dollars.items():
            already = sells.get(asset, 0.0)
            capacity = dollars - already
            take = remaining * (dollars / current_value)
            sells[asset] = already + min(capacity, take)

    trades = [
        _trade(asset, current_value, weights.get(asset, 0.0),
               target_weights.get(asset, 0.0), -dollars)
        for asset, dollars in sells.items() if dollars > 0.0
    ]
    trades.sort(key=lambda t: t.trade_value)  # biggest sells (most negative) first
    return CashFlowPlan(
        trades=trades,
        cash_deployed=-need,
        cash_remaining=0.0,
        set_aside=0.0,
    )

