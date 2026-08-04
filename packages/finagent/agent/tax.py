# finagent/agent/tax.py

from __future__ import annotations

from pydantic_ai import models

from finkritintel.capability.tax import TAX_CAPABILITY

from finagent.agent.base import DEFAULT_LANGUAGE, CapabilityAgent
from finagent.store import DEFAULT_PORTFOLIO_ID

TAX_INSTRUCTIONS = (
    "You are a portfolio tax analyst. Use the available tools to describe the "
    "current tax position of the user's portfolio at today's prices, then answer "
    "plainly. Cover unrealized gains and losses, tax-loss harvesting candidates, "
    "and the split between long term (held at least a year) and short term "
    "holdings. Always state the numbers and whether an amount is long or short "
    "term, since the tax treatment differs. Report harvestable losses net of the "
    "wash sale exclusion the tool applies, and name any holding it blocked. "
    "You describe the tax position, you do not place trades and you do not "
    "rebalance, so present harvesting as a candidate list, not an instruction. "
    "If a tool returns an error or empty values, say the computation could not be "
    "completed and why, rather than guessing. This is not tax advice, and the "
    "user should confirm anything with a qualified professional. "
    f"The user has a single portfolio, registered with id '{DEFAULT_PORTFOLIO_ID}'. "
    "Use that id for any portfolio-level tool unless the user names a different one."
)


class TaxAgent(CapabilityAgent):
    """
    Tax specialist. Conversational only (inherited ask/ask_async): the LLM picks a
    tax tool and explains the result. Read-only, it reports gains, harvest
    candidates, and the holding-period split, and never rebalances or trades.
    Tax-aware rebalancing is a later composition over the optimizer, see the
    deferred rebalancing task.
    """

    def __init__(
        self,
        model: models.Model | models.KnownModelName | str | None = None,
        instructions: str = TAX_INSTRUCTIONS,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        super().__init__(
            TAX_CAPABILITY, model=model, instructions=instructions, language=language,
        )
