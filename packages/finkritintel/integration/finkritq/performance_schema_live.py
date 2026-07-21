from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.data import DataRegistry
from finkritq.datatype import WeightingBasis
from finkritq.portfolio import Portfolio

# Fields mirror the live wrapper implementations (and the pre-fetched schemas).
# Portfolio returns are always simple, so there is no return-convention `method`.


@dataclass(frozen=True, slots=True)
class PortfolioTotalReturnLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class PortfolioAnnualizedReturnLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioSharpeRatioLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    risk_free_rate: float = 0.0
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioSortinoRatioLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    risk_free_rate: float = 0.0
    target: float = 0.0
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioCalmarRatioLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    periods_per_year: int = 252
