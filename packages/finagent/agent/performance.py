# finagent/agent/performance.py

from __future__ import annotations

from datetime import date

from pydantic_ai import models

from finkritintel.capability.performance import PERFORMANCE_CAPABILITY
from finkritq.datatype import WeightingBasis

from finagent.agent.base import CapabilityAgent
from finagent.deps import AgentDeps
from finagent.report.performance import (
    PerformanceMetric,
    PortfolioPerformanceReport,
    compose_portfolio_performance_report,
)
from finagent.store import DEFAULT_PORTFOLIO_ID

PERFORMANCE_INSTRUCTIONS = (
    "You are a portfolio performance analyst. Use the available tools to compute "
    "return and risk-adjusted performance metrics (total return, annualized return, "
    "Sharpe, Sortino, Calmar) for the user's portfolio, then answer plainly. "
    "Always state the number and the lookback window it was computed over. Returns "
    "are simple, not log. Ratios are annualized unless stated otherwise, and use the "
    "given risk-free rate (0 by default). If a metric cannot be computed (missing "
    "data), say so rather than guessing. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}'. "
    "Use that id for any portfolio-level tool unless the user names a different one."
)


class PerformanceAgent(CapabilityAgent):
    """
    Performance specialist. Two surfaces, exactly like RiskAgent:
      - report(): deterministic, no LLM -- the reproducible report/dashboard path.
      - ask()   : conversational (inherited) -- LLM picks tools, free-text answer.

    Kept separate from RiskAgent (one capability, one domain, one agent). A
    combined risk+performance answer is a fan-out over both specialists at call
    time, not a single fatter agent.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = PERFORMANCE_INSTRUCTIONS,
    ) -> None:
        # model is optional: .report() is deterministic and needs no LLM; only
        # .ask() requires a model (enforced lazily by CapabilityAgent).
        super().__init__(PERFORMANCE_CAPABILITY, model=model, instructions=instructions)

    def report(
        self,
        portfolio_id: str,
        deps: AgentDeps,
        metrics: frozenset[PerformanceMetric] | set[PerformanceMetric] | str = "core",
        *,
        basis: WeightingBasis = WeightingBasis.BUY_AND_HOLD,
        risk_free_rate: float = 0.0,
        target: float = 0.0,
        periods_per_year: int = 252,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PortfolioPerformanceReport:
        portfolio = deps.store.get_portfolio(portfolio_id)
        return compose_portfolio_performance_report(
            portfolio,
            deps.registry,
            metrics,
            basis=basis,
            risk_free_rate=risk_free_rate,
            target=target,
            periods_per_year=periods_per_year,
            start=start,
            end=end,
            interval=interval,
        )
