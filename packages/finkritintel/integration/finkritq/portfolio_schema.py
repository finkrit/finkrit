

from __future__ import annotations

from dataclasses import dataclass

from finkritq.anal.returns import ReturnCalculationMethod
from finkritq.datatype import PriceHistory, VaREstimationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData

# NOTE: `basis` mirrors the finkritq portfolio_* implementations (the contract
# test enforces schema<->impl parity). Each default matches its function's
# default basis; see finkritq WeightingBasis.


@dataclass(frozen=True, slots=True)
class VolatilityInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class VarianceInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class SemivarianceInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class DownsideDeviationInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class DrawdownInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class MaximumDrawdownInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class ValueAtRiskInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class ConditionalValueAtRiskInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    return_method: ReturnCalculationMethod = ReturnCalculationMethod.LOG
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class BetaInput:
    portfolio_data: PortfolioData
    benchmark_history: PriceHistory
    method: ReturnCalculationMethod = ReturnCalculationMethod.LOG


@dataclass(frozen=True, slots=True)
class MarginalRiskInput:
    portfolio_data: PortfolioData


@dataclass(frozen=True, slots=True)
class ComponentRiskInput:
    portfolio_data: PortfolioData
