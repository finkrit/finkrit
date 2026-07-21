# finagent/agent/optimization.py

from __future__ import annotations

from pydantic_ai import models

from finkritintel.capability.optimization import OPTIMIZATION_CAPABILITY

from finagent.agent.base import CapabilityAgent
from finagent.store import DEFAULT_PORTFOLIO_ID

OPTIMIZATION_INSTRUCTIONS = (
    "You are a portfolio optimization analyst. Use the available tools to compute "
    "optimal allocations for the user's portfolio, then answer plainly. State the "
    "weight for each holding as a percentage, note that the weights sum to 100%, "
    "and name which objective produced them (minimum-variance for lowest risk, "
    "maximum-Sharpe for best risk-adjusted return). The weights are long-only on a "
    "shrunk covariance unless the user asks otherwise. These are suggested targets, "
    "not trades, be clear you are proposing an allocation, not executing anything. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}', "
    "use that id for any portfolio-level tool unless the user names a different one."
)


class OptimizationAgent(CapabilityAgent):
    """
    Optimization specialist. Conversational only for now (inherited ask/ask_async):
    the LLM picks an optimizer tool and explains the resulting allocation. No
    deterministic report surface yet, an allocation report composer lands later.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = OPTIMIZATION_INSTRUCTIONS,
    ) -> None:
        super().__init__(OPTIMIZATION_CAPABILITY, model=model, instructions=instructions)
