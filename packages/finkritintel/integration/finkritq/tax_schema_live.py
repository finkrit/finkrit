from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.data import DataRegistry
from finkritq.portfolio import Portfolio

# Input schemas for the live tax bindings. `portfolio` is resolved from a
# portfolio id and `registry` is injected from deps, exactly like the risk and
# performance live schemas. The remaining fields are plain scalars the model can
# supply. `as_of` defaults to the valuation date (today) when left unset.


@dataclass(frozen=True, slots=True)
class PortfolioUnrealizedGainsLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    as_of: date | None = None


@dataclass(frozen=True, slots=True)
class PortfolioHarvestableLossesLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    as_of: date | None = None
    min_loss: float = 0.0
    wash_sale_window_days: int = 30


@dataclass(frozen=True, slots=True)
class PortfolioHoldingPeriodBreakdownLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    as_of: date | None = None
