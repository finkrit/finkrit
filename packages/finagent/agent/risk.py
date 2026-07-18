# finagent/agent/risk.py

from __future__ import annotations

from datetime import date

from pydantic_ai import models

from finkritintel.capability.risk import RISK_CAPABILITY
from finkritq.asset import Asset

from finagent.agent.base import CapabilityAgent
from finagent.deps import AgentDeps
from finagent.report.composer import compose_portfolio_risk_report
from finagent.report.metric import RiskMetric
from finagent.report.report import PortfolioRiskReport
from finagent.store import DEFAULT_PORTFOLIO_ID

RISK_INSTRUCTIONS = (
    "You are a portfolio risk analyst. Use the available tools to compute risk "
    "metrics for the user's portfolio or an individual asset, then answer plainly. "
    "Always state the number, the lookback window it was computed over, and the "
    "benchmark where relevant. Volatility and related measures are annualized; "
    "Value at Risk is a 95% one-period figure unless stated otherwise. If a metric "
    "cannot be computed (e.g. no benchmark, missing data), say so rather than guessing. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}' -- "
    "use that id for any portfolio-level tool unless the user names a different one."
)


class RiskAgent(CapabilityAgent):
    """
    Risk specialist. Two surfaces:
      - report(): deterministic, no LLM -- the reproducible report/dashboard path.
      - ask()   : conversational (inherited) -- LLM picks tools, free-text answer.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = RISK_INSTRUCTIONS,
    ) -> None:
        # model is optional: .report() is deterministic and needs no LLM; only
        # .ask() requires a model (enforced lazily by CapabilityAgent).
        super().__init__(RISK_CAPABILITY, model=model, instructions=instructions)

    def report(
        self,
        portfolio_id: str,
        deps: AgentDeps,
        metrics: frozenset[RiskMetric] | set[RiskMetric] | str = "core",
        *,
        benchmark: Asset | None = None,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PortfolioRiskReport:
        portfolio = deps.store.get_portfolio(portfolio_id)
        return compose_portfolio_risk_report(
            portfolio,
            deps.registry,
            metrics,
            benchmark=benchmark,
            start=start,
            end=end,
            interval=interval,
        )

