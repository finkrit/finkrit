# finkritintel/tool/rebalance.py
"""
Tool contract for tax-aware rebalancing.

This is the composition the tax contracts point at: target weights come from an
optimizer, the sells that reach the target are realized lot by lot under a
capital gains budget. It lives in its own module because it is neither a pure
optimization leaf nor part of the read-only tax lens, it proposes trades.

Proposes, never places. The output is a plan, and every consumer downstream is
expected to present it as one.

Deliberately not surfaced yet: the Policy-driven variant (nothing above this
layer constructs a Policy today) and wash sale replacement mappings (a model
supplied ticker mapping is a hallucination vector, replacements belong to a
typed surface, not a chat argument).
"""
from finkritintel.tool.contract import ToolContract


PORTFOLIO_REBALANCE_COMPARE = ToolContract(
    name="portfolio_rebalance_compare",
    description=(
        "Run the same tax-aware rebalance under every named strategy and "
        "return the plans side by side, so the tradeoff between tax cost and "
        "remaining drift is visible in one table. The strategies are fixed: "
        "'full' sells each overweight all the way to target, 'band_edge' sells "
        "only the excess beyond the tolerance band, 'partial_fill' sells to "
        "target but scales budget-breaching sells down to exactly exhaust the "
        "gain budget. Target weights, prices, budget, and lot method are held "
        "constant across rows, which is what makes them comparable. Use when "
        "the user is weighing options or asks what a gentler rebalance would "
        "save. For a user who already knows what they want, use "
        "portfolio_tax_aware_rebalance instead. Proposes plans, never trades."
    ),
    category="rebalance",
    tags=("portfolio", "rebalance", "tax", "compare"),
)

PORTFOLIO_TAX_AWARE_REBALANCE = ToolContract(
    name="portfolio_tax_aware_rebalance",
    description=(
        "Propose the sell side of a rebalance toward an optimized allocation "
        "while capping the net realized capital gain at a dollar budget. "
        "Computes target weights from the chosen objective (minimum variance or "
        "maximum Sharpe), then realizes the overweight positions drift-first: "
        "losses are always taken (harvesting), gains only until the budget is "
        "reached, and remaining gain-sells are deferred and reported. Lots are "
        "chosen by the sale method, HIFO by default, which minimizes the gain "
        "realized per share sold. Use for questions about rebalancing without a "
        "big tax bill, how much rebalancing a tax budget buys, or what selling "
        "toward the optimum would cost in tax. This proposes a plan, it does "
        "not execute trades."
    ),
    category="rebalance",
    tags=("portfolio", "rebalance", "tax", "optimization"),
)
