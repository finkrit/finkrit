# finkritintel/integration/finq/asset_schema.py

from __future__ import annotations

from dataclasses import dataclass

from finkritq.transform.returns import ReturnCalculationMethod
from finkritq.datatype import PriceHistory, VaREstimationMethod


@dataclass(frozen=True, slots=True)
class AssetVolatilityInput:
    history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetVarianceInput:
    history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetSemivarianceInput:
    history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetDownsideDeviationInput:
    history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class AssetDrawdownInput:
    history: PriceHistory


@dataclass(frozen=True, slots=True)
class AssetMaximumDrawdownInput:
    history: PriceHistory


@dataclass(frozen=True, slots=True)
class AssetValueAtRiskInput:
    history: PriceHistory
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class AssetConditionalValueAtRiskInput:
    history: PriceHistory
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class AssetBetaInput:
    asset_history: PriceHistory  # matches beta(asset_history, benchmark_history, method)
    benchmark_history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG

