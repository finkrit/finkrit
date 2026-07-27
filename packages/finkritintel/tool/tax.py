# finkritintel/tool/tax.py
"""
Tool contracts for the read-only tax lens.

These expose finkritq's tax-lot analytics (unrealized gains, tax-loss harvest
candidates, and the long versus short term holding split) as callable tools.
They are read-only, they describe the current tax position and never place a
trade. Tax-aware rebalancing is deliberately out of scope here, it needs target
weights from the optimizer or a policy object, which is a composition rather
than a leaf tool.
"""
from finkritintel.tool.contract import ToolContract


PORTFOLIO_UNREALIZED_GAINS = ToolContract(
    name="portfolio_unrealized_gains",
    description=(
        "Report the portfolio's unrealized capital gains and losses at current "
        "prices, in total and per holding, with the total split into long term "
        "and short term by holding period. Use for questions about paper gains, "
        "embedded gains, or how much would be taxable if sold today."
    ),
    category="tax",
    tags=("portfolio", "tax", "gains"),
)

PORTFOLIO_HARVESTABLE_LOSSES = ToolContract(
    name="portfolio_harvestable_losses",
    description=(
        "Find tax-loss harvesting candidates at current prices, the lots trading "
        "below cost, with the total harvestable loss split long versus short "
        "term. Holdings bought within the wash sale window are excluded and "
        "reported separately. Use for tax-loss harvesting and year-end tax "
        "planning questions."
    ),
    category="tax",
    tags=("portfolio", "tax", "harvest"),
)

PORTFOLIO_HOLDING_PERIOD_BREAKDOWN = ToolContract(
    name="portfolio_holding_period_breakdown",
    description=(
        "Break the portfolio's cost basis and market value into long term (held "
        "at least a year) and short term buckets, with the long term fraction of "
        "market value. Use for questions about how much of the portfolio would "
        "qualify for long term capital gains treatment."
    ),
    category="tax",
    tags=("portfolio", "tax", "holding-period"),
)
