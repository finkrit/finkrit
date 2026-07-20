from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.anal.returns import ReturnCalculationMethod
from finkritq.data import DataRegistry
from finkritq.datatype import VaREstimationMethod, WeightingBasis
from finkritq.portfolio import Portfolio

# `basis` mirrors the finkritq portfolio_* implementations (and the pre-fetched
# schemas in portfolio_schema.py), so the live tools expose the same
# constant-mix vs buy-and-hold choice. Each default matches its metric's default
# basis; see finkritq WeightingBasis.


@dataclass(frozen=True, slots=True)
class PortfolioVolatilityLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioVarianceLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioSemivarianeLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioDownsideDeviationLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class PortfolioDrawdownLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class PortfolioMaximumDrawdownLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class PortfolioValueAtRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class PortfolioConditionalValueAtRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class PortfolioBetaLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    benchmark_history_or_asset: object  # PriceHistory (pre-fetched) or Asset (live)
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG


@dataclass(frozen=True, slots=True)
class PortfolioMarginalRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"


@dataclass(frozen=True, slots=True)
class PortfolioComponentRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"


