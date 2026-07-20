from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.transform.returns import ReturnCalculationMethod
from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import VaREstimationMethod


@dataclass(frozen=True, slots=True)
class AssetVolatilityLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetVarianceLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetSemivarianeLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetDownsideDeviationLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetDrawdownLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"


@dataclass(frozen=True, slots=True)
class AssetMaximumDrawdownLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"


@dataclass(frozen=True, slots=True)
class AssetValueAtRiskLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class AssetConditionalValueAtRiskLiveInput:
    asset: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class AssetBetaLiveInput:
    asset: Asset
    benchmark: Asset
    registry: DataRegistry
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG

