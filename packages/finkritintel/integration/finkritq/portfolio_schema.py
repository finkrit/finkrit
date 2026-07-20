

from __future__ import annotations

from dataclasses import dataclass

from finkritq.datatype import PriceHistory, VaREstimationMethod, WeightingBasis
from finkritq.portfolio import PortfolioData

# NOTE: fields mirror the finkritq portfolio_* implementations (the contract test
# enforces schema<->impl parity). Portfolio returns are always simple, so there
# is no return-convention `method` at the portfolio level; see finkritq
# WeightingBasis / PortfolioData.constant_mix_returns.


@dataclass(frozen=True, slots=True)
class VolatilityInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class VarianceInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.CONSTANT_MIX
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class SemivarianceInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    target: float = 0.0
    annualized: bool = True
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class DownsideDeviationInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
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
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class ConditionalValueAtRiskInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    method: VaREstimationMethod = VaREstimationMethod.HISTORICAL
    confidence: float = 0.95
    n_simulations: int = 100_000
    random_state: int | None = None


@dataclass(frozen=True, slots=True)
class BetaInput:
    portfolio_data: PortfolioData
    benchmark_history: PriceHistory


@dataclass(frozen=True, slots=True)
class MarginalRiskInput:
    portfolio_data: PortfolioData


@dataclass(frozen=True, slots=True)
class ComponentRiskInput:
    portfolio_data: PortfolioData
