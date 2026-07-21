# finkrit/packages/finkritq/optimize/meanvariance.py
"""
Closed-form mean-variance optimization, numpy only, no solver.

These are the *unconstrained* (budget-only, wᵀ1 = 1) optima, which have exact
matrix solutions. Long-only and bounded variants need a quadratic-program solver
and live separately. Everything here operates on an annualized covariance matrix
Σ and (where needed) an expected-return vector μ, both produced from a
PortfolioData on the same simple-return series so they share a time base.

Numerically we solve Σx = v (np.linalg.solve) rather than forming Σ⁻¹, which is
more stable. A singular Σ (collinear assets, or fewer periods than assets) raises
LinAlgError, surfaced, not silently pinv'd.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from finkritq.anal.risk import covariance_matrix
from finkritq.asset import Asset
from finkritq.optimize.expected_returns import expected_returns
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class FrontierPoint:
    """One point on the efficient frontier: its target return, the volatility it
    achieves, and the weights that get there (aligned to the asset order used)."""

    expected_return: float
    volatility: float
    weights: NDArray[np.float64]


# ---------------------------------------------------------------------------
# Weight solvers (operate on Σ / μ arrays)
# ---------------------------------------------------------------------------

def minimum_variance_weights(cov: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Global minimum-variance portfolio: the weights that minimize wᵀΣw subject
    only to wᵀ1 = 1.

        w = Σ⁻¹1 / (1ᵀΣ⁻¹1)

    Ignores expected returns entirely, it is the leftmost point of the frontier.
    """
    ones = np.ones(cov.shape[0], dtype=np.float64)
    z = np.linalg.solve(cov, ones)          # Σ⁻¹1
    return z / z.sum()                       # z.sum() == 1ᵀΣ⁻¹1


def tangency_weights(
    cov: NDArray[np.float64],
    expected_excess_returns: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Tangency (maximum-Sharpe) portfolio, given excess returns μ_e = μ - rf:

        w = Σ⁻¹μ_e / (1ᵀΣ⁻¹μ_e)

    Maximizes (wᵀμ - rf) / sqrt(wᵀΣw) over wᵀ1 = 1. Assumes 1ᵀΣ⁻¹μ_e > 0 (the
    usual case when the max-Sharpe portfolio is net long), if it is negative the
    normalization flips sign, which signals the excess-return assumptions, not a
    code bug.
    """
    z = np.linalg.solve(cov, expected_excess_returns)   # Σ⁻¹μ_e
    return z / z.sum()


def _frontier_coefficients(
    cov: NDArray[np.float64],
    mu: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], float, float, float, float]:
    # The four scalars of the Merton efficient-frontier solution.
    ones = np.ones(len(mu), dtype=np.float64)
    inv_ones = np.linalg.solve(cov, ones)   # Σ⁻¹1
    inv_mu = np.linalg.solve(cov, mu)        # Σ⁻¹μ
    a = float(ones @ inv_ones)               # 1ᵀΣ⁻¹1
    b = float(ones @ inv_mu)                 # 1ᵀΣ⁻¹μ
    c = float(mu @ inv_mu)                    # μᵀΣ⁻¹μ
    d = a * c - b * b
    return inv_ones, inv_mu, a, b, c, d


def target_return_weights(
    cov: NDArray[np.float64],
    mu: NDArray[np.float64],
    target_return: float,
) -> NDArray[np.float64]:
    """
    Minimum-variance weights achieving a target expected return:

        minimize wᵀΣw   subject to   wᵀμ = target,  wᵀ1 = 1

    Closed form w = g + h·target (two-fund theorem), where g and h are fixed
    combinations of Σ⁻¹1 and Σ⁻¹μ. g sums to 1 and h sums to 0, so wᵀ1 = 1 holds
    for every target.
    """
    inv_ones, inv_mu, a, b, c, d = _frontier_coefficients(cov, mu)
    g = (c * inv_ones - b * inv_mu) / d
    h = (a * inv_mu - b * inv_ones) / d
    return g + h * target_return


def efficient_frontier(
    cov: NDArray[np.float64],
    mu: NDArray[np.float64],
    n_points: int = 25,
) -> list[FrontierPoint]:
    """
    Sample the efficient frontier across target returns spanning the assets'
    expected-return range, returning each target with the volatility it achieves.
    """
    targets = np.linspace(float(mu.min()), float(mu.max()), n_points)
    points: list[FrontierPoint] = []
    for target in targets:
        weights = target_return_weights(cov, mu, float(target))
        points.append(
            FrontierPoint(
                expected_return=float(target),
                volatility=portfolio_volatility_from_weights(weights, cov),
                weights=weights,
            )
        )
    return points


# ---------------------------------------------------------------------------
# Portfolio statistics for a given weight vector
# ---------------------------------------------------------------------------

def portfolio_return_from_weights(
    weights: NDArray[np.float64],
    mu: NDArray[np.float64],
) -> float:
    return float(weights @ mu)


def portfolio_variance_from_weights(
    weights: NDArray[np.float64],
    cov: NDArray[np.float64],
) -> float:
    return float(weights @ cov @ weights)


def portfolio_volatility_from_weights(
    weights: NDArray[np.float64],
    cov: NDArray[np.float64],
) -> float:
    return float(np.sqrt(portfolio_variance_from_weights(weights, cov)))


def portfolio_sharpe_from_weights(
    weights: NDArray[np.float64],
    mu: NDArray[np.float64],
    cov: NDArray[np.float64],
    risk_free_rate: float = 0.0,
) -> float:
    vol = portfolio_volatility_from_weights(weights, cov)
    if vol == 0.0:
        return float("nan")
    return (portfolio_return_from_weights(weights, mu) - risk_free_rate) / vol


# ---------------------------------------------------------------------------
# PortfolioData entry points (fetch Σ / μ, return weights keyed by asset)
# ---------------------------------------------------------------------------

def _weights_by_asset(
    portfolio_data: PortfolioData,
    weights: NDArray[np.float64],
) -> dict[Asset, float]:
    return {asset: float(w) for asset, w in zip(portfolio_data.assets, weights)}


def minimum_variance_portfolio(
    portfolio_data: PortfolioData,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> dict[Asset, float]:
    """Global minimum-variance weights for the portfolio's assets."""
    cov = covariance_matrix(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    return _weights_by_asset(portfolio_data, minimum_variance_weights(cov))


def maximum_sharpe_portfolio(
    portfolio_data: PortfolioData,
    risk_free_rate: float = 0.0,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> dict[Asset, float]:
    """Tangency (max-Sharpe) weights for the portfolio's assets."""
    cov = covariance_matrix(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    mu = expected_returns(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    return _weights_by_asset(portfolio_data, tangency_weights(cov, mu - risk_free_rate))


def efficient_frontier_portfolio(
    portfolio_data: PortfolioData,
    n_points: int = 25,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> list[FrontierPoint]:
    """The efficient frontier for the portfolio's assets."""
    cov = covariance_matrix(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    mu = expected_returns(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    return efficient_frontier(cov, mu, n_points=n_points)
