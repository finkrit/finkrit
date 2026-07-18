# finkritintel/tests/tool/test_binding_contract.py
"""
I-1: enforce that each ToolBinding's declared input_schema actually matches the
signature of its implementation.

ToolBinding.execute forwards **kwargs straight through, so nothing at runtime
checks that the schema and the implementation agree -- add a parameter to a
finkritq function and forget to update the schema, and the drift is invisible
until an agent call fails. This test makes that drift a collection-time failure
across every binding the integration package exports.
"""
from __future__ import annotations

import dataclasses
import inspect

import pytest

import finkritintel.integration.finkritq as integration
from finkritintel.tool.binding import ToolBinding


def _all_bindings() -> list[ToolBinding]:
    return [v for v in vars(integration).values() if isinstance(v, ToolBinding)]


def _binding_id(binding: ToolBinding) -> str:
    # Contract names are shared by the pre-fetched/live variants, so key the
    # test id on the (distinct) schema class name.
    return binding.input_schema.__name__


_BINDINGS = _all_bindings()


def test_integration_package_exports_bindings():
    # Guard against the collection silently finding nothing (e.g. an import
    # rename) and the parametrized test vacuously passing.
    assert len(_BINDINGS) >= 40  # ~20 pre-fetched + ~20 live


@pytest.mark.parametrize("binding", _BINDINGS, ids=[_binding_id(b) for b in _BINDINGS])
def test_schema_fields_match_implementation_parameters(binding: ToolBinding):
    schema_fields = {f.name for f in dataclasses.fields(binding.input_schema)}
    impl_params = set(inspect.signature(binding.implementation).parameters)

    missing_in_impl = schema_fields - impl_params
    missing_in_schema = impl_params - schema_fields

    assert not missing_in_impl, (
        f"{binding.contract.name}: schema fields not accepted by implementation: {missing_in_impl}"
    )
    assert not missing_in_schema, (
        f"{binding.contract.name}: implementation params not declared in schema: {missing_in_schema}"
    )
