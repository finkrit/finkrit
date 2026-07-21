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
from finkritq.optimize.lotselection import LotSaleMethod, SaleResult, select_lots_to_sell
from finkritq.optimize.rebalance import rebalance_to_model
from finkritq.portfolio import PortfolioData, Position


@dataclass(frozen=True, slots=True)
class TaxRebalanceSell:
    asset: Asset
    sell_value: float          # dollars (positive magnitude)
    sale: SaleResult           # the lots realized and their gain split
    is_harvest: bool           # realized a net loss

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


def tax_aware_rebalance(
    portfolio_data: PortfolioData,
    target_weights: dict[Asset, float],
    prices: dict[Asset, Decimal],
    as_of: date,
    gain_budget: float = float("inf"),
    tolerance: float = 0.0,
    method: LotSaleMethod = LotSaleMethod.HIFO,
    replacements: dict[Asset, Asset] | None = None,
) -> TaxRebalancePlan:
    """
    Rebalance toward ``target_weights`` under a ``gain_budget`` (max net realized
    capital gain in dollars, default unlimited). Losses are always realized, gains
    are realized drift-first until the net gain would exceed the budget, then
    deferred. ``replacements`` maps a harvested asset to a substitute bought with
    the proceeds.
    """
    replacements = replacements or {}
    trades = rebalance_to_model(portfolio_data, target_weights, tolerance=tolerance)
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

        if gain > 0 and budget is not None and net_gain + gain > budget:
            deferred.append(asset)     # would breach the gain budget -> defer
            continue

        executed.append(TaxRebalanceSell(
            asset=asset,
            sell_value=abs(trade.trade_value),
            sale=sale,
            is_harvest=gain < 0,
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
    )
