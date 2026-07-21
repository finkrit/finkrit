from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.data import DataRegistry
from finkritq.portfolio import Portfolio

# Fields mirror the live wrapper implementations. `portfolio` is resolved from a
# portfolio_id and `registry` is injected from deps, neither is LLM-facing, the
# rest are plain scalars the model can supply.


@dataclass(frozen=True, slots=True)
class MinimumVarianceLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    long_only: bool = True


@dataclass(frozen=True, slots=True)
class MaximumSharpeLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    risk_free_rate: float = 0.0
    long_only: bool = True
