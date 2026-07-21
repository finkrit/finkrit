# finkrit/packages/finkritq/optimize/meanvariance.py
"""
Mean-variance optimization: closed-form for the unconstrained case, a quadratic
program for the realistic constrained one.

The closed-form solvers here are the *unconstrained* (budget-only, wᵀ1 = 1)
optima, which have exact matrix solutions and can hand back short or levered
weights. The PortfolioData entry points instead default to the *constrained*
solve (long-only, plus any Policy box constraints) via a small SLSQP program,
because raw sample inputs make the unconstrained optima wildly unstable, extreme,
often short. Everything operates on an annualized covariance matrix Σ and (where
needed) an expected-return vector μ from a PortfolioData on the same
simple-return series, so they share a time base.

Two robustness pieces condition the inputs the entry points feed the solver:

    * Ledoit-Wolf shrinkage pulls the noisy sample covariance toward a scaled
      identity, which tames spurious correlations and guarantees a well
      conditioned (positive-definite) Σ even when assets outnumber observations.
    * Long-only / Policy box constraints keep the weights sane and enforceable.

The closed forms solve Σx = v (np.linalg.solve) rather than forming Σ⁻¹. A
singular raw Σ raises LinAlgError there, surfaced, not silently pinv'd, one more
reason the entry points shrink first.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from finkritq.anal.risk import covariance_matrix
from finkritq.asset import Asset
from finkritq.datatype import ReturnCalculationMethod
from finkritq.optimize.expected_returns import expected_returns
from finkritq.policy import Policy, RestrictionKind
from finkritq.portfolio import PortfolioData

# Per-asset weight bound (lower, upper). None means unbounded on that side.
Bound = tuple[float | None, float | None]


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
# Covariance shrinkage (Ledoit-Wolf toward a scaled identity)
# ---------------------------------------------------------------------------

def ledoit_wolf_shrinkage(
    returns: NDArray[np.float64],
) -> tuple[NDArray[np.float64], float]:
    """
    Ledoit-Wolf linear shrinkage of a sample covariance toward a scaled identity.

    ``returns`` is (n_assets, n_periods) of per-period returns. Returns the shrunk
    per-period covariance and the shrinkage intensity delta in [0, 1] (0 = pure
    sample, 1 = pure scaled identity). The target is ``m * I`` with ``m`` the
    average sample variance, and delta is the data-driven optimum from Ledoit and
    Wolf (2004), the ratio of estimation error to the distance from the target.
    """
    X = np.asarray(returns, dtype=np.float64)
    n_assets, n_periods = X.shape
    demeaned = X - X.mean(axis=1, keepdims=True)
    sample = (demeaned @ demeaned.T) / n_periods   # 1/T convention (Ledoit-Wolf)

    identity = np.eye(n_assets)
    m = np.trace(sample) / n_assets
    d2 = float(np.sum((sample - m * identity) ** 2))

    # Estimation error of the sample covariance: average squared deviation of the
    # per-period outer products from the sample mean, capped at d2.
    b2_sum = 0.0
    for t in range(n_periods):
        x_t = demeaned[:, t]
        b2_sum += float(np.sum((np.outer(x_t, x_t) - sample) ** 2))
    b2_bar = b2_sum / (n_periods ** 2)
    b2 = min(b2_bar, d2)

    delta = 0.0 if d2 == 0.0 else float(np.clip(b2 / d2, 0.0, 1.0))
    shrunk = delta * m * identity + (1.0 - delta) * sample
    return shrunk, delta


def _covariance(
    portfolio_data: PortfolioData,
    shrinkage: bool,
    annualized: bool,
    periods_per_year: int,
) -> NDArray[np.float64]:
    # The covariance the entry points optimize on: Ledoit-Wolf shrunk by default
    # (stable and always positive-definite), or the raw sample if shrinkage off.
    if not shrinkage:
        return covariance_matrix(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    returns = portfolio_data.return_matrix(ReturnCalculationMethod.SIMPLE)
    shrunk, _ = ledoit_wolf_shrinkage(returns)
    return shrunk * periods_per_year if annualized else shrunk


# ---------------------------------------------------------------------------
# Constrained solvers (SLSQP quadratic program with box + budget constraints)
# ---------------------------------------------------------------------------

def _budget_constraint() -> dict:
    return {"type": "eq", "fun": lambda w: float(w.sum() - 1.0)}


def _solve(objective, n_assets: int, bounds: list[Bound], constraints: list[dict]) -> NDArray[np.float64]:
    # Equal-weight start, SLSQP with the budget and any extra constraints. Renormalize
    # the result so the budget holds exactly despite solver tolerance.
    w0 = np.full(n_assets, 1.0 / n_assets)
    result = minimize(objective, w0, method="SLSQP", bounds=bounds,
                      constraints=[_budget_constraint(), *constraints])
    weights = np.clip(result.x, 0.0, None) if all(b[0] == 0.0 for b in bounds) else result.x
    total = weights.sum()
    return weights / total if total != 0.0 else weights


def constrained_minimum_variance_weights(
    cov: NDArray[np.float64],
    bounds: list[Bound],
) -> NDArray[np.float64]:
    """Minimum-variance weights subject to the budget and per-asset box bounds."""
    return _solve(lambda w: float(w @ cov @ w), cov.shape[0], bounds, [])


def constrained_max_sharpe_weights(
    cov: NDArray[np.float64],
    expected_excess_returns: NDArray[np.float64],
    bounds: list[Bound],
) -> NDArray[np.float64]:
    """Maximum-Sharpe weights subject to the budget and per-asset box bounds."""
    def neg_sharpe(w: NDArray[np.float64]) -> float:
        vol = float(np.sqrt(w @ cov @ w))
        return 0.0 if vol == 0.0 else -float(w @ expected_excess_returns) / vol

    return _solve(neg_sharpe, cov.shape[0], bounds, [])


def constrained_target_return_weights(
    cov: NDArray[np.float64],
    mu: NDArray[np.float64],
    target_return: float,
    bounds: list[Bound],
) -> NDArray[np.float64]:
    """Minimum-variance weights hitting ``target_return``, box-bounded."""
    hit_target = {"type": "eq", "fun": lambda w: float(w @ mu - target_return)}
    return _solve(lambda w: float(w @ cov @ w), cov.shape[0], bounds, [hit_target])


def constrained_efficient_frontier(
    cov: NDArray[np.float64],
    mu: NDArray[np.float64],
    bounds: list[Bound],
    n_points: int = 25,
) -> list[FrontierPoint]:
    """
    Box-constrained efficient frontier, sampled across the feasible return range.

    For long-only weights the achievable returns span the individual assets'
    expected returns, so the sweep runs from the minimum to the maximum mu.
    """
    targets = np.linspace(float(mu.min()), float(mu.max()), n_points)
    points: list[FrontierPoint] = []
    for target in targets:
        weights = constrained_target_return_weights(cov, mu, float(target), bounds)
        points.append(FrontierPoint(
            expected_return=portfolio_return_from_weights(weights, mu),
            volatility=portfolio_volatility_from_weights(weights, cov),
            weights=weights,
        ))
    return points


# ---------------------------------------------------------------------------
# Policy box constraints
# ---------------------------------------------------------------------------

def bounds_for(
    assets: tuple[Asset, ...],
    long_only: bool,
    policy: Policy | None,
    current_weights: dict[Asset, float] | None,
) -> list[Bound]:
    """
    Per-asset weight bounds from a long-only default and a Policy's restrictions.

    DO_NOT_HOLD pins the asset to 0, MAX_WEIGHT caps it, MIN_WEIGHT floors it, and
    DO_NOT_BUY caps it at its current weight (no adding). Long-only sets the
    default box to [0, 1], otherwise the default is unbounded.
    """
    low_default: float | None = 0.0 if long_only else None
    high_default: float | None = 1.0 if long_only else None

    by_asset: dict[Asset, list[RestrictionKind]] = {}
    if policy is not None:
        for restriction in policy.restrictions:
            by_asset.setdefault(restriction.asset, []).append(restriction)

    bounds: list[Bound] = []
    for asset in assets:
        low, high = low_default, high_default
        for restriction in by_asset.get(asset, []):
            if restriction.kind is RestrictionKind.DO_NOT_HOLD:
                low, high = 0.0, 0.0
            elif restriction.kind is RestrictionKind.MAX_WEIGHT:
                high = restriction.limit if high is None else min(high, restriction.limit)
            elif restriction.kind is RestrictionKind.MIN_WEIGHT:
                low = restriction.limit if low is None else max(low, restriction.limit)
            elif restriction.kind is RestrictionKind.DO_NOT_BUY and current_weights is not None:
                cap = current_weights.get(asset, 0.0)
                high = cap if high is None else min(high, cap)
        bounds.append((low, high))
    return bounds


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
    long_only: bool = True,
    policy: Policy | None = None,
    shrinkage: bool = True,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> dict[Asset, float]:
    """
    Minimum-variance weights for the portfolio's assets.

    Defaults to the realistic solve: long-only, on a Ledoit-Wolf shrunk
    covariance. Pass a ``policy`` to add its box constraints, ``long_only=False``
    for the unconstrained closed form, ``shrinkage=False`` for the raw sample
    covariance.
    """
    cov = _covariance(portfolio_data, shrinkage, annualized, periods_per_year)
    if not long_only and policy is None:
        return _weights_by_asset(portfolio_data, minimum_variance_weights(cov))
    bounds = bounds_for(portfolio_data.assets, long_only, policy, portfolio_data.weights)
    return _weights_by_asset(portfolio_data, constrained_minimum_variance_weights(cov, bounds))


def maximum_sharpe_portfolio(
    portfolio_data: PortfolioData,
    risk_free_rate: float = 0.0,
    long_only: bool = True,
    policy: Policy | None = None,
    shrinkage: bool = True,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> dict[Asset, float]:
    """
    Maximum-Sharpe (tangency) weights for the portfolio's assets.

    Same defaults as ``minimum_variance_portfolio``: long-only on a shrunk
    covariance, with an optional ``policy`` for box constraints.
    """
    cov = _covariance(portfolio_data, shrinkage, annualized, periods_per_year)
    mu = expected_returns(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    excess = mu - risk_free_rate
    if not long_only and policy is None:
        return _weights_by_asset(portfolio_data, tangency_weights(cov, excess))
    bounds = bounds_for(portfolio_data.assets, long_only, policy, portfolio_data.weights)
    return _weights_by_asset(portfolio_data, constrained_max_sharpe_weights(cov, excess, bounds))


def efficient_frontier_portfolio(
    portfolio_data: PortfolioData,
    n_points: int = 25,
    long_only: bool = True,
    policy: Policy | None = None,
    shrinkage: bool = True,
    annualized: bool = True,
    periods_per_year: int = 252,
) -> list[FrontierPoint]:
    """
    The efficient frontier for the portfolio's assets.

    Long-only on a shrunk covariance by default (with an optional ``policy``),
    or the unconstrained closed-form frontier when ``long_only=False`` and no
    policy is given.
    """
    cov = _covariance(portfolio_data, shrinkage, annualized, periods_per_year)
    mu = expected_returns(portfolio_data, annualized=annualized, periods_per_year=periods_per_year)
    if not long_only and policy is None:
        return efficient_frontier(cov, mu, n_points=n_points)
    bounds = bounds_for(portfolio_data.assets, long_only, policy, portfolio_data.weights)
    return constrained_efficient_frontier(cov, mu, bounds, n_points=n_points)
