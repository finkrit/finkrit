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

# The widest risk question, in calls. It used to be seven, one tool per metric.
# Now portfolio_risk and asset_risk each take a metric list, so the widest
# question is both of them, once each, whatever it asks for.
WIDEST_RISK_QUESTION = ("portfolio_risk", "asset_risk")


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
        # DEFAULT_TOOL_RETRIES times. Every call in the widest question going
        # wrong the maximum number of times must still fit.
        exhaustive_retries = len(WIDEST_RISK_QUESTION) * DEFAULT_TOOL_RETRIES
        assert SPECIALIST_USAGE_LIMITS.tool_calls_limit >= (
            len(WIDEST_RISK_QUESTION) + exhaustive_retries
        )

    def test_the_budget_no_longer_scales_with_holdings(self):
        # The whole point of the collapse. A per holding question used to cost
        # one call per holding, which fit at twelve and failed at two hundred,
        # so no fixed ceiling could ever cover it. asset_risk takes a ticker
        # list, so the call count is the same either way.
        asset_tool = next(
            t for t in RISK_CAPABILITY.tools if t.contract.name == "asset_risk"
        )
        assert "assets" in asset_tool.input_schema.__dataclass_fields__

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

    def test_every_capability_now_fits_inside_the_budget(self):
        # Risk used to be the exception, twenty tools against a ceiling of
        # twelve, so an exhaustive answer was structurally impossible. With the
        # collapse there is no capability a specialist cannot work through, and
        # the ceiling is a runaway backstop rather than a cap on thoroughness.
        for capability in (
            RISK_CAPABILITY, PERFORMANCE_CAPABILITY, OPTIMIZATION_CAPABILITY, TAX_CAPABILITY,
        ):
            assert (
                len(_tool_names(capability))
                <= SPECIALIST_USAGE_LIMITS.tool_calls_limit
            ), capability.name

    def test_a_capability_agent_takes_it_by_default(self):
        agent = CapabilityAgent(capability=RISK_CAPABILITY)
        assert agent._usage_limits is SPECIALIST_USAGE_LIMITS
        assert DEFAULT_USAGE_LIMITS is SPECIALIST_USAGE_LIMITS


class TestPerAssetFanOutIsFixedByShapeNotByCeiling:
    """This used to assert the opposite: that a metric for every holding
    overflowed by design, and that raising the ceiling was the wrong answer
    because one call per holding fits at twelve and fails at two hundred.

    That was right about the ceiling and wrong to leave the shape alone. The
    fix was the tool, not the number, so these now pin the property that made
    the ceiling irrelevant."""

    def test_no_risk_tool_takes_a_single_ticker(self):
        # The regression that would bring the whole problem back.
        for tool in RISK_CAPABILITY.tools:
            assert "asset" not in tool.input_schema.__dataclass_fields__, tool.contract.name

    def test_any_portfolio_size_costs_the_same_two_calls(self):
        # Twelve holdings or two hundred, the widest question is
        # portfolio_risk plus asset_risk, and both fit with room to retry.
        for holdings in (12, 200, 5000):
            assert len(WIDEST_RISK_QUESTION) <= SPECIALIST_USAGE_LIMITS.tool_calls_limit, holdings
