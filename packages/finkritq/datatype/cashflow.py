# finkrit/packages/finkritq/datatype/cashflow.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type


@dataclass(frozen=True, slots=True)
class CashFlow:
    """
    An external cash flow into or out of a portfolio on a date.

    Sign convention (portfolio's point of view): ``amount > 0`` is a contribution
    (money in), ``amount < 0`` is a withdrawal (money out). External flows are the
    thing that makes a naive return wrong, they change the portfolio's value
    without being investment performance, which is exactly why time-weighted and
    money-weighted returns exist to handle them (see performance.flows).

    Turning a list of these into the per-period array those functions take is
    ``flows_to_series``, which lives with them in anal/performance/flows.py. It
    converts one representation into another rather than naming a concept, so it
    is a transform and not vocabulary, and this package holds vocabulary.
    """

    date: date_type
    amount: float
