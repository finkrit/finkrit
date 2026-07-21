from __future__ import annotations

from dataclasses import dataclass

from finkritq.datatype import WeightingBasis
from finkritq.portfolio import PortfolioData

# Fields mirror the finkritq portfolio_* performance implementations (the contract
# test enforces schema<->impl parity). Portfolio returns are always simple, so
# there is no return-convention `method` at the portfolio level.


@dataclass(frozen=True, slots=True)
class TotalReturnInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD


@dataclass(frozen=True, slots=True)
class AnnualizedReturnInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class SharpeRatioInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    risk_free_rate: float = 0.0
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class SortinoRatioInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    risk_free_rate: float = 0.0
    target: float = 0.0
    periods_per_year: int = 252


@dataclass(frozen=True, slots=True)
class CalmarRatioInput:
    portfolio_data: PortfolioData
    basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD
    periods_per_year: int = 252
