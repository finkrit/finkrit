# finagent/report/tax_signals.py
"""
Tax signals: the deterministic, actionable tax view the dashboard renders.

A signal is data plus a threshold plus a suggested action plus what the action
is worth in dollars, which is what separates a dashboard a wealth manager acts
on from a table of numbers. Three families, all computed in code with no LLM
in the path:

  - harvest: lots underwater and clear of the wash sale window, each with the
    estimated tax saving of realizing the loss today.
  - wash sale warnings: tickers where a recent purchase would forfeit the loss.
  - long term countdowns: short term lots near the 365 day boundary. A gain
    lot is worth holding until it crosses (the gain gets the long term rate),
    a loss lot is worth harvesting before it (a short term loss offsets the
    higher taxed gains first). The rate spread prices both.

Unlike the LLM tax tools, these rows carry lot level detail (id, quantity,
acquisition date). The boundary that keeps lot internals out of the model does
not apply here: this report goes straight from code to the owner's dashboard,
and "which lots" is exactly what makes the signal actionable.

Savings are estimates at assumed marginal rates, defaulted and overridable per
request, and the rates used are echoed in the report so the dashboard can
label them as assumptions. This is analytics, not tax advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finkritintel.integration.finkritq.tax_live import spot_prices
from finkritq.data import DataRegistry
from finkritq.optimize import harvest_candidates, long_term_transitions
from finkritq.portfolio import Portfolio

# Assumed marginal rates: a common bracket for short term (taxed as income)
# and the headline long term capital gains rate. Deliberately round, clearly
# labeled in the payload, and overridable per request.
DEFAULT_SHORT_TERM_RATE = 0.3
DEFAULT_LONG_TERM_RATE = 0.15

# Long term countdown horizon. Wide enough to plan a sale around, short enough
# that the list stays a handful of rows instead of half the portfolio.
DEFAULT_COUNTDOWN_DAYS = 45


@dataclass(frozen=True, slots=True)
class HarvestSignal:
    """One lot worth harvesting today, with what doing so is worth."""

    ticker: str
    lot_id: str
    quantity: float
    acquired: date
    cost_basis: float
    market_value: float
    unrealized_loss: float   # positive magnitude
    is_long_term: bool
    # unrealized_loss times the rate for its term. What the harvest saves in
    # tax this year, assuming gains exist to offset.
    estimated_saving: float


@dataclass(frozen=True, slots=True)
class CountdownSignal:
    """One short term lot near the long term boundary, and which way to act."""

    ticker: str
    lot_id: str
    quantity: float
    acquired: date
    market_value: float
    unrealized_gain: float   # signed: positive gain, negative loss
    transition_date: date
    days_until: int
    # "hold" for a gain lot (sell after the boundary at the long term rate),
    # "harvest_now" for a loss lot (realize while the loss is still short
    # term). Decided here in code so every consumer words it the same way.
    action: str
    # abs(unrealized_gain) times the short/long rate spread: what acting on
    # the right side of the boundary is worth versus the wrong side.
    estimated_saving: float


@dataclass(frozen=True, slots=True)
class TaxSignalsReport:
    """The full signal set for one portfolio, one as_of date."""

    as_of: date
    # The assumptions behind every estimated_saving, echoed so the dashboard
    # can display them as assumptions rather than facts.
    short_term_rate: float
    long_term_rate: float

    total_harvestable_loss: float
    estimated_harvest_saving: float
    harvest: list[HarvestSignal]
    wash_sale_blocked: list[str]
    countdowns: list[CountdownSignal]


def compose_tax_signals(
    portfolio: Portfolio,
    registry: DataRegistry,
    *,
    as_of: date | None = None,
    short_term_rate: float = DEFAULT_SHORT_TERM_RATE,
    long_term_rate: float = DEFAULT_LONG_TERM_RATE,
    min_loss: float = 0.0,
    wash_sale_window_days: int = 30,
    countdown_days: int = DEFAULT_COUNTDOWN_DAYS,
) -> TaxSignalsReport:
    """
    Compute every tax signal off one price read, so the harvest rows and the
    countdown rows can never disagree about what a lot is worth.
    """
    if not 0.0 <= long_term_rate <= short_term_rate <= 1.0:
        # An inverted spread silently flips the countdown advice (holding a
        # gain lot would "cost" money), so refuse rather than mislead.
        raise ValueError(
            "Rates must satisfy 0 <= long_term_rate <= short_term_rate <= 1."
        )

    as_of = as_of or date.today()
    prices = spot_prices(portfolio, registry)

    report = harvest_candidates(
        portfolio,
        prices,
        as_of,
        min_loss=Decimal(str(min_loss)),
        wash_sale_window_days=wash_sale_window_days,
    )

    harvest: list[HarvestSignal] = []
    estimated_harvest_saving = 0.0
    for candidate in report.candidates:
        rate = long_term_rate if candidate.is_long_term else short_term_rate
        saving = round(float(candidate.unrealized_loss) * rate, 2)
        estimated_harvest_saving += saving
        harvest.append(
            HarvestSignal(
                ticker=candidate.asset.ticker,
                lot_id=candidate.lot.id,
                quantity=float(candidate.lot.quantity),
                acquired=candidate.lot.acquired,
                cost_basis=round(float(candidate.cost_basis), 2),
                market_value=round(float(candidate.market_value), 2),
                unrealized_loss=round(float(candidate.unrealized_loss), 2),
                is_long_term=candidate.is_long_term,
                estimated_saving=saving,
            )
        )

    rate_spread = short_term_rate - long_term_rate
    countdowns = [
        CountdownSignal(
            ticker=transition.asset.ticker,
            lot_id=transition.lot.id,
            quantity=float(transition.lot.quantity),
            acquired=transition.lot.acquired,
            market_value=round(float(transition.market_value), 2),
            unrealized_gain=round(float(transition.unrealized_gain), 2),
            transition_date=transition.transition_date,
            days_until=transition.days_until,
            action="hold" if transition.unrealized_gain >= 0 else "harvest_now",
            estimated_saving=round(
                abs(float(transition.unrealized_gain)) * rate_spread, 2
            ),
        )
        for transition in long_term_transitions(
            portfolio, prices, as_of, within_days=countdown_days
        )
    ]

    return TaxSignalsReport(
        as_of=as_of,
        short_term_rate=short_term_rate,
        long_term_rate=long_term_rate,
        total_harvestable_loss=round(float(report.total_harvestable_loss), 2),
        estimated_harvest_saving=round(estimated_harvest_saving, 2),
        harvest=harvest,
        wash_sale_blocked=[asset.ticker for asset in report.wash_sale_blocked],
        countdowns=countdowns,
    )
