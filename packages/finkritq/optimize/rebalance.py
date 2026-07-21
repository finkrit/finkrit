# finkrit/packages/finkritq/optimize/rebalance.py
"""
Rebalance a portfolio toward a target model, the way trading platforms do it:
compare current weights to the model, and only trade assets whose *drift* exceeds
a tolerance band, ranked by drift severity so the biggest offenders surface first.

This is pure weights math and stays in finq: given current holdings and a target
weight vector, it returns the dollar trades. Which specific lots a sell realizes
is tax-aware lot selection (see lotselection.py), this module speaks in dollar 
amounts per asset.
"""
from __future__ import annotations

from dataclasses import dataclass

from finkritq.asset import Asset
from finkritq.policy import Policy, RestrictionKind
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class RebalanceTrade:
    """A single proposed trade to move one asset toward its model weight."""

    asset: Asset
    current_weight: float
    target_weight: float
    drift: float          # current - target (positive => overweight => sell)
    trade_value: float    # dollars, positive => buy, negative => sell
    reason: str = "drift" # why the trade was proposed (see rebalance_to_policy)

    @property
    def is_buy(self) -> bool:
        # bool(...) so a numpy-float trade_value yields a real Python bool
        # (np.True_/np.False_ fail identity checks like `is True`).
        return bool(self.trade_value > 0.0)


def rebalance_to_model(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
    tolerance: float = 0.0,
) -> list[RebalanceTrade]:
    """
    Trades to move the portfolio from its current weights toward ``target_weights``.

    ``tolerance`` is the drift band (as a weight fraction, e.g. 0.05 = 5%): an
    asset is traded only if ``abs(current - target) > tolerance``. With
    ``tolerance = 0`` this is a full rebalance to the exact model. An asset in the
    model but not held is a buy (current 0), an asset held but not in the model is
    a full sell (target 0).

    Trades bring the asset all the way to its target (not just to the band edge),
    which is the common "rebalance to target" convention. Dollar sizing uses the
    portfolio's current total market value. Returned sorted by drift severity, so
    the most out-of-line positions come first (drift-based trade scoring).
    """
    total_value = float(portfolio_data.value[-1])
    current = portfolio_data.weights  # dict[Asset, float], sums to 1

    assets = set(current) | set(target_weights)
    trades: list[RebalanceTrade] = []
    for asset in assets:
        current_weight = current.get(asset, 0.0)
        target_weight = target_weights.get(asset, 0.0)
        drift = current_weight - target_weight

        if abs(drift) <= tolerance:
            continue

        trades.append(
            RebalanceTrade(
                asset=asset,
                current_weight=current_weight,
                target_weight=target_weight,
                drift=drift,
                trade_value=(target_weight - current_weight) * total_value,
            )
        )

    trades.sort(key=lambda trade: abs(trade.drift), reverse=True)
    return trades


def total_drift(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
) -> float:
    """
    Total absolute drift from the model: sum of |current - target| over all
    assets. A single number for "how far out of line is this portfolio", used to
    decide whether a rebalance is even worth triggering (and to rank accounts
    across a book). 0.0 means perfectly on-model.
    """
    current = portfolio_data.weights
    assets = set(current) | set(target_weights)
    return sum(
        abs(current.get(asset, 0.0) - target_weights.get(asset, 0.0))
        for asset in assets
    )


def rebalance_to_policy(
    portfolio_data: PortfolioData,
    policy: Policy,
) -> list[RebalanceTrade]:
    """
    Trades to bring the portfolio into line with a ``Policy``, honoring its bands
    and holding restrictions. This is ``rebalance_to_model`` that respects the
    rules, the proposal side of supervision (see policy.compliance for the
    detection side).

    Rules applied per asset:

      * Restrictions clamp the effective target: DO_NOT_HOLD forces it to 0,
        MAX_WEIGHT caps it, MIN_WEIGHT floors it.
      * An asset is traded only if it breaches its own drift band OR a restriction
        it holds is currently violated (a forced trade even inside the band).
      * DO_NOT_BUY suppresses buys: if the proposed trade would add to the asset it
        is dropped, so an underweight restricted name is simply left alone.

    Effective targets are not renormalized, so clamping a holding down leaves the
    freed weight as cash (underinvested) rather than reshuffling the model. Each
    trade carries a ``reason`` (drift, do_not_hold, max_weight, min_weight).
    Returned sorted by drift severity.
    """
    total_value = float(portfolio_data.value[-1])
    current = portfolio_data.weights

    do_not_hold = {r.asset for r in policy.restrictions if r.kind is RestrictionKind.DO_NOT_HOLD}
    do_not_buy = {r.asset for r in policy.restrictions if r.kind is RestrictionKind.DO_NOT_BUY}
    max_cap = {r.asset: r.limit for r in policy.restrictions if r.kind is RestrictionKind.MAX_WEIGHT}
    min_floor = {r.asset: r.limit for r in policy.restrictions if r.kind is RestrictionKind.MIN_WEIGHT}

    assets = set(current) | set(policy.target_weights) | do_not_hold | do_not_buy \
        | set(max_cap) | set(min_floor)

    trades: list[RebalanceTrade] = []
    for asset in assets:
        current_weight = current.get(asset, 0.0)

        # Effective target after restriction clamps.
        if asset in do_not_hold:
            target_weight = 0.0
        else:
            target_weight = policy.target_weights.get(asset, 0.0)
            if asset in max_cap:
                target_weight = min(target_weight, max_cap[asset])
            if asset in min_floor:
                target_weight = max(target_weight, min_floor[asset])

        drift = current_weight - target_weight
        band = policy.band_for(asset).allowed(target_weight)

        # A currently-violated restriction forces a trade even inside the band,
        # otherwise trade only on a band breach.
        if asset in do_not_hold and current_weight > 0.0:
            reason = "do_not_hold"
        elif asset in max_cap and current_weight > max_cap[asset]:
            reason = "max_weight"
        elif asset in min_floor and current_weight < min_floor[asset]:
            reason = "min_weight"
        elif abs(drift) > band:
            reason = "drift"
        else:
            continue

        trade_value = (target_weight - current_weight) * total_value

        # Cannot add to a DO_NOT_BUY name: drop the buy, leave it underweight.
        if trade_value > 0.0 and asset in do_not_buy:
            continue

        trades.append(
            RebalanceTrade(
                asset=asset,
                current_weight=current_weight,
                target_weight=target_weight,
                drift=drift,
                trade_value=trade_value,
                reason=reason,
            )
        )

    trades.sort(key=lambda trade: abs(trade.drift), reverse=True)
    return trades
