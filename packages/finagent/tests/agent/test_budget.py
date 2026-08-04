# finagent/tests/agent/test_budget.py
"""
The tool budgets.

Numbers picked by hand go stale silently, so these assert the reasoning behind
them against the tool surface that is actually there: the orchestrator must be
able to reach every specialist, and a specialist must be able to answer the
widest question its capability supports without running out of room to correct
a rejected call.
"""
from __future__ import annotations

import warnings

from finkritintel.capability.optimization import OPTIMIZATION_CAPABILITY
from finkritintel.capability.performance import PERFORMANCE_CAPABILITY
from finkritintel.capability.risk import RISK_CAPABILITY
from finkritintel.capability.tax import TAX_CAPABILITY

from finagent.agent.base import (
    DEFAULT_TOOL_RETRIES,
    DEFAULT_USAGE_LIMITS,
    ORCHESTRATOR_USAGE_LIMITS,
    SPECIALIST_USAGE_LIMITS,
    CapabilityAgent,
)
from finagent.agent.orchestrator import Orchestrator

warnings.filterwarnings("ignore", message="Could not generate return schema")

# What the orchestrator delegates to. Its budget is a count of these.
SPECIALIST_COUNT = 4

# The widest honest risk question, the one the specialist budget is sized for.
WIDEST_RISK_QUESTION = (
    "portfolio_volatility",
    "portfolio_value_at_risk",
    "portfolio_conditional_value_at_risk",
    "portfolio_maximum_drawdown",
    "portfolio_beta",
    "portfolio_marginal_contribution_to_risk",
    "portfolio_component_contribution_to_risk",
)


def _tool_names(capability) -> set[str]:
    return {binding.contract.name for binding in capability.tools}


class TestRequestsAreDerivedFromToolCalls:
    """A model that issues its calls one at a time, which is what a local model
    does, spends one request per call plus one to write the answer. Sizing for
    that leaves the tool count as the only ceiling that ever bites."""

    def test_every_budget_allows_a_fully_serial_run(self):
        for limits in (ORCHESTRATOR_USAGE_LIMITS, SPECIALIST_USAGE_LIMITS):
            assert limits.request_limit == limits.tool_calls_limit + 1

    def test_the_budgets_are_distinct_objects(self):
        # Sharing one would put a delegation and a metric on the same scale.
        assert ORCHESTRATOR_USAGE_LIMITS is not SPECIALIST_USAGE_LIMITS


class TestOrchestratorBudget:

    def test_it_can_reach_every_specialist(self):
        assert ORCHESTRATOR_USAGE_LIMITS.tool_calls_limit >= SPECIALIST_COUNT

    def test_it_leaves_room_to_go_back_to_one(self):
        # Reading performance's answer can raise a question for risk. A budget
        # of exactly SPECIALIST_COUNT would forbid that.
        assert ORCHESTRATOR_USAGE_LIMITS.tool_calls_limit > SPECIALIST_COUNT

    def test_it_is_tighter_than_a_specialist_budget(self):
        # One delegation is an entire nested run, so the orchestrator spending
        # as freely as a specialist is a spiral, not thoroughness.
        assert (
            ORCHESTRATOR_USAGE_LIMITS.tool_calls_limit
            < SPECIALIST_USAGE_LIMITS.tool_calls_limit
        )

    def test_the_orchestrator_takes_it_by_default(self):
        orchestrator = Orchestrator(
            model=None, risk=None, performance=None, optimization=None, tax=None
        )
        assert orchestrator._usage_limits is ORCHESTRATOR_USAGE_LIMITS


class TestSpecialistBudget:

    def test_the_widest_risk_question_is_real(self):
        # If a rename lands, this fails here rather than silently shrinking
        # what the budget is claimed to cover.
        assert set(WIDEST_RISK_QUESTION) <= _tool_names(RISK_CAPABILITY)

    def test_it_covers_the_widest_question_with_room_to_correct(self):
        # A rejected call spends a slot, and a call may be retried
        # DEFAULT_TOOL_RETRIES times. Half the question going wrong once must
        # still fit.
        headroom = (
            SPECIALIST_USAGE_LIMITS.tool_calls_limit - len(WIDEST_RISK_QUESTION)
        )
        assert headroom >= len(WIDEST_RISK_QUESTION) // 2
        assert headroom >= DEFAULT_TOOL_RETRIES

    def test_the_narrow_capabilities_can_call_everything_they_have(self):
        # Performance, optimization, and tax are small enough that an
        # exhaustive answer is legitimate, so the budget must not forbid it.
        for capability in (
            PERFORMANCE_CAPABILITY, OPTIMIZATION_CAPABILITY, TAX_CAPABILITY,
        ):
            assert (
                len(_tool_names(capability))
                <= SPECIALIST_USAGE_LIMITS.tool_calls_limit
            )

    def test_risk_is_the_one_capability_it_cannot_exhaust(self):
        # Twenty risk tools against a budget of twelve is intentional: calling
        # all twenty is not an answer, it is a model that has not decided what
        # the question was.
        assert (
            len(_tool_names(RISK_CAPABILITY))
            > SPECIALIST_USAGE_LIMITS.tool_calls_limit
        )

    def test_a_capability_agent_takes_it_by_default(self):
        agent = CapabilityAgent(capability=RISK_CAPABILITY)
        assert agent._usage_limits is SPECIALIST_USAGE_LIMITS
        assert DEFAULT_USAGE_LIMITS is SPECIALIST_USAGE_LIMITS


class TestPerAssetFanOutIsNotSizedFor:
    """One call per holding grows with the portfolio, so no fixed ceiling
    covers it. The budget stays sized to metric breadth and the shape gets
    fixed by decomposing the question."""

    def test_a_metric_for_every_holding_overflows_by_design(self):
        holdings = 12  # the portfolio that first hit this
        assert holdings > SPECIALIST_USAGE_LIMITS.tool_calls_limit - len(
            WIDEST_RISK_QUESTION
        )
