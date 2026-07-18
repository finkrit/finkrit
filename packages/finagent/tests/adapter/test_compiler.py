# finagent/tests/adapter/test_compiler.py
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest
from pydantic_ai import ModelRetry, RunContext

from finkritintel.capability.risk import RISK_CAPABILITY

from finagent.adapter.compiler import compile_capability, compile_tool
from finagent.deps import AgentDeps
from finagent.store import InMemoryStore
from finagent.tests.fixtures import make_portfolio, make_registry, make_stock


def _binding(name: str):
    return next(b for b in RISK_CAPABILITY.tools if b.contract.name == name)


class TestCompileTool:

    def test_every_binding_compiles_to_a_real_function(self):
        for binding in RISK_CAPABILITY.tools:
            fn = compile_tool(binding)
            assert callable(fn)
            assert fn.__name__ == binding.contract.name

    def test_memoized_same_binding_returns_the_same_function_object(self):
        # F-7: exec-codegen is real work; a hashable ToolBinding should only
        # pay it once for the process lifetime, not once per agent construction.
        binding = _binding("portfolio_volatility")
        assert compile_tool(binding) is compile_tool(binding)

    def test_signature_has_no_annotation_stringification_bug(self):
        # Regression: compile() silently inherits `from __future__ import
        # annotations` from the compiler module unless dont_inherit=True,
        # which stringifies every annotation instead of resolving real types.
        fn = compile_tool(_binding("portfolio_volatility"))
        sig = inspect.signature(fn)
        assert sig.parameters["portfolio_id"].annotation is str
        assert sig.parameters["start"].default is None

    def test_ctx_is_first_param(self):
        fn = compile_tool(_binding("portfolio_volatility"))
        params = list(inspect.signature(fn).parameters)
        assert params[0] == "ctx"

    def test_portfolio_field_becomes_portfolio_id(self):
        fn = compile_tool(_binding("portfolio_volatility"))
        params = inspect.signature(fn).parameters
        assert "portfolio_id" in params
        assert "portfolio" not in params

    def test_asset_field_becomes_ticker(self):
        fn = compile_tool(_binding("asset_volatility"))
        params = inspect.signature(fn).parameters
        assert "ticker" in params
        assert "asset" not in params

    def test_asset_beta_has_both_ticker_and_benchmark_ticker(self):
        fn = compile_tool(_binding("asset_beta"))
        params = inspect.signature(fn).parameters
        assert "ticker" in params
        assert "benchmark_ticker" in params

    def test_portfolio_beta_benchmark_history_or_asset_becomes_benchmark_ticker(self):
        fn = compile_tool(_binding("portfolio_beta"))
        params = inspect.signature(fn).parameters
        assert "benchmark_ticker" in params
        assert "benchmark_history_or_asset" not in params

    def test_registry_never_appears_in_signature(self):
        for binding in RISK_CAPABILITY.tools:
            fn = compile_tool(binding)
            assert "registry" not in inspect.signature(fn).parameters

    def test_docstring_carries_contract_description(self):
        binding = _binding("portfolio_volatility")
        fn = compile_tool(binding)
        assert fn.__doc__ == binding.contract.description


class TestCompileToolExecution:

    def _deps(self) -> AgentDeps:
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        store.register_asset(make_stock("BENCH"))
        return AgentDeps(store=store, registry=make_registry())

    def _ctx(self, deps: AgentDeps) -> RunContext:
        ctx = MagicMock(spec=RunContext)
        ctx.deps = deps
        return ctx

    def test_portfolio_tool_resolves_and_computes(self):
        fn = compile_tool(_binding("portfolio_volatility"))
        ctx = self._ctx(self._deps())
        result = fn(ctx, "port-1")
        assert isinstance(result, float)
        assert result > 0

    def test_asset_tool_resolves_and_computes(self):
        fn = compile_tool(_binding("asset_volatility"))
        ctx = self._ctx(self._deps())
        result = fn(ctx, "AAA")
        assert isinstance(result, float)
        assert result > 0

    def test_beta_tool_resolves_both_tickers(self):
        fn = compile_tool(_binding("asset_beta"))
        ctx = self._ctx(self._deps())
        result = fn(ctx, "AAA", "BENCH")
        assert isinstance(result, float)

    def test_unknown_portfolio_id_raises_model_retry_not_key_error(self):
        fn = compile_tool(_binding("portfolio_volatility"))
        ctx = self._ctx(self._deps())
        with pytest.raises(ModelRetry):
            fn(ctx, "does-not-exist")


class TestOutputAdapters:
    """The 4 NDArray-returning tools must return JSON-serializable dicts,
    not raw numpy arrays (which crash tool-return serialization)."""

    def _ctx(self):
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        store.register_asset(make_stock("BENCH"))
        ctx = MagicMock(spec=RunContext)
        ctx.deps = AgentDeps(store=store, registry=make_registry())
        return ctx

    @pytest.mark.parametrize(
        "name,args",
        [
            ("portfolio_drawdown", ("port-1",)),
            ("asset_drawdown", ("AAA",)),
            ("portfolio_marginal_contribution_to_risk", ("port-1",)),
            ("portfolio_component_contribution_to_risk", ("port-1",)),
        ],
    )
    def test_adapted_tool_returns_dict_not_ndarray(self, name, args):
        fn = compile_tool(_binding(name))
        result = fn(self._ctx(), *args)
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "name,args", [("portfolio_drawdown", ("port-1",)), ("asset_drawdown", ("AAA",))]
    )
    def test_drawdown_summary_shape(self, name, args):
        fn = compile_tool(_binding(name))
        result = fn(self._ctx(), *args)
        assert set(result) == {"max_drawdown", "current_drawdown", "periods"}
        assert result["max_drawdown"] <= 0.0

    @pytest.mark.parametrize(
        "name",
        ["portfolio_marginal_contribution_to_risk", "portfolio_component_contribution_to_risk"],
    )
    def test_contribution_keyed_by_ticker(self, name):
        fn = compile_tool(_binding(name))
        result = fn(self._ctx(), "port-1")
        assert set(result) == {"AAA", "BBB"}
        assert all(isinstance(v, float) for v in result.values())

    def test_adapted_tool_return_annotation_is_dict(self):
        fn = compile_tool(_binding("portfolio_drawdown"))
        assert inspect.signature(fn).return_annotation is dict

    def test_unadapted_tool_still_returns_scalar(self):
        fn = compile_tool(_binding("portfolio_volatility"))
        store = InMemoryStore()
        store.register_portfolio(make_portfolio())
        ctx = MagicMock(spec=RunContext)
        ctx.deps = AgentDeps(store=store, registry=make_registry())
        assert isinstance(fn(ctx, "port-1"), float)


class TestCompileCapability:

    def test_id_and_description_carried_over(self):
        capability = compile_capability(RISK_CAPABILITY)
        assert capability.id == RISK_CAPABILITY.name
        assert capability.description == RISK_CAPABILITY.description

    def test_tool_count_matches(self):
        capability = compile_capability(RISK_CAPABILITY)
        assert len(capability.tools) == len(RISK_CAPABILITY.tools)

    def test_defer_loading_defaults_false(self):
        capability = compile_capability(RISK_CAPABILITY)
        assert capability.defer_loading is False

    def test_defer_loading_can_be_enabled(self):
        capability = compile_capability(RISK_CAPABILITY, defer_loading=True)
        assert capability.defer_loading is True
