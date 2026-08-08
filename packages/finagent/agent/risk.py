# finagent/agent/risk.py

from __future__ import annotations

from datetime import date

from pydantic_ai import models

from finkritq.asset import Asset

from finkritintel.capability.risk import RISK_CAPABILITY

from finkritcore.report.composer import compose_portfolio_risk_report
from finkritcore.report.metric import RiskMetric
from finkritcore.report.report import PortfolioRiskReport
from finkritcore.store import DEFAULT_PORTFOLIO_ID

from finagent.agent.base import DEFAULT_LANGUAGE, CapabilityAgent
from finagent.deps import AgentDeps


RISK_INSTRUCTIONS = (
    "You are a portfolio risk analyst. You have exactly two tools: "
    "portfolio_risk for the portfolio as a whole, and asset_risk for its "
    "individual holdings. Both take a list of metrics, so ask for everything "
    "the question needs in one call rather than calling repeatedly. "
    # The parameter that makes a per holding question answerable at all. The
    # model holds an opaque portfolio id and can only ever learn a ticker by
    # receiving one in a result, so left to itself it invents them.
    "For anything about 'my assets', 'each stock', or 'my holdings', call "
    "asset_risk and do NOT pass tickers: omitting them covers every holding. "
    "Never guess a ticker. "
    # The recovery path that keeps a fumbled metric list from becoming a
    # confidently wrong answer.
    "Every result names the metrics it computed and the ones that were "
    "available but not requested. If what the user asked for is missing from "
    "'computed' and present in 'available', call again asking for it, and "
    "never present a metric you did have as though it were the one they wanted. "
    # Every result carries window and units, so the model never has to infer
    # either. It used to, and got both wrong: a fraction reported as "$204.77"
    # and a sampling frequency reported as the lookback ("over past 1 day").
    # Observed: a model handed bare tickers annotated them from memory and
    # labelled V as "Vanguard Utilities ETF". It is Visa.
    "A result may carry a 'names' entry mapping tickers to security names. Use "
    "those and only those. Never add a company name from your own knowledge, "
    "and if a ticker has no name given, use the ticker alone. "
    "Every result carries a 'window' saying what period it covers and a 'units' "
    "entry for each metric. State the window from that field, never from "
    "'sampling', which is only how often the series was measured. Report each "
    "number in the units given: a fraction is a fraction, so 0.0205 is 2.05%, "
    "and never a currency amount. You were not given position values and cannot "
    "convert one. "
    "Always state the number, the window, and the benchmark where relevant. When "
    "the user does not name a benchmark, do not ask for one: omit "
    "benchmark_ticker and the S&P 500 (^GSPC) is used, then say so. "
    "If a metric appears under 'errors' rather than in the results, tell the "
    "user that one could not be computed and give the reason reported, most "
    "often too few overlapping trading days or missing price data over the "
    "window. Never invent a financial explanation for a failed or empty result, "
    "and never offer to substitute an assumption the tool did not ask for. In "
    "particular marginal_contribution and component_contribution derive each "
    "holding's weight from its current market value and take no target weights, "
    "so a failure there is a data problem, not missing weights, and asking the "
    "user for weights is wrong. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}'. "
    "Use that id unless the user names a different one."
)


class RiskAgent(CapabilityAgent):
    """
    Risk specialist. Two surfaces:
      - report(): deterministic, no LLM, the reproducible report/dashboard path.
      - ask()   : conversational (inherited), LLM picks tools, free-text answer.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = RISK_INSTRUCTIONS,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        # model is optional: .report() is deterministic and needs no LLM; only
        # .ask() requires a model (enforced lazily by CapabilityAgent).
        super().__init__(
            RISK_CAPABILITY, model=model, instructions=instructions, language=language,
        )

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

