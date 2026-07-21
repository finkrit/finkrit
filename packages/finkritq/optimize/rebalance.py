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
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class RebalanceTrade:
    """A single proposed trade to move one asset toward its model weight."""

    asset: Asset
    current_weight: float
    target_weight: float
    drift: float          # current - target (positive => overweight => sell)
    trade_value: float    # dollars, positive => buy, negative => sell

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
