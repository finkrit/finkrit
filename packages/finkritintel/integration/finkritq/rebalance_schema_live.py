# finkritintel/integration/finkritq/rebalance_schema_live.py
"""
Input schema for the live tax-aware rebalance binding.

`portfolio` is resolved from a portfolio id and `registry` is injected from
deps, like every other live schema. The rest are scalars the model supplies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.data import DataRegistry
from finkritq.datatype import LotSaleMethod, RebalanceSizing
from finkritq.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class TaxAwareRebalanceLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    # Which optimizer produces the target weights. Validated in the wrapper, a
    # bad value raises with the allowed names so the model can correct itself.
    objective: str = "min_variance"
    # Max net realized capital gain in dollars. None means unlimited, which
    # turns the run into a plain drift-first rebalance with lot-aware sells.
    gain_budget: float | None = None
    # How lots are consumed within each sell. HIFO realizes the least gain per
    # share, FIFO is the IRS default ordering, LIFO sells the newest first.
    method: LotSaleMethod = LotSaleMethod.HIFO
    # Ignore drifts at or below this fraction (0.02 = 2 points of weight), so
    # tiny offsets do not generate noise trades.
    tolerance: float = 0.0
    # Where a triggered trade lands: on the target, or just inside the band
    # (TO_BAND_EDGE, which requires a positive tolerance and trades less per
    # event at the cost of remaining drift).
    sizing: RebalanceSizing = RebalanceSizing.TO_TARGET
    # Scale a budget-breaching sell down to exactly exhaust the remaining gain
    # room instead of deferring it whole.
    partial_fill: bool = False
    # Valuation date for the long versus short term split. Today when unset.
    as_of: date | None = None
    # History window handed to the optimizer, same contract as the optimizer
    # tools: unset means the registry default lookback.
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True, slots=True)
class RebalanceCompareLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    objective: str = "min_variance"
    gain_budget: float | None = None
    method: LotSaleMethod = LotSaleMethod.HIFO
    # Nonzero default, unlike the single-plan tool: the band_edge row is
    # meaningless without a band, and this tool exists to show all the rows.
    tolerance: float = 0.02
    as_of: date | None = None
    start: date | None = None
    end: date | None = None
