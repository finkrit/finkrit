# finagent/adapter/compiler.py

from __future__ import annotations

import dataclasses
import functools
import typing
from typing import Any, Callable

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import Capability as PydanticCapability

from finkritintel.capability.base import Capability as FinkritCapability
from finkritintel.tool.binding import ToolBinding

from finagent.adapter.output import OUTPUT_ADAPTERS
from finagent.adapter.resolve import FIELD_RESOLVERS, INJECTED_FIELDS, resolve_field
from finagent.deps import AgentDeps

_MISSING = dataclasses.MISSING


def _execute_or_retry(binding: ToolBinding, /, **kwargs: Any) -> Any:
    # A finkritq computation that cannot proceed on the given data raises
    # ValueError with the reason (too few overlapping observations, missing or
    # bad prices, an unknown ticker). Translate that into a ModelRetry so the
    # reason reaches the model and it reports the real problem to the user,
    # instead of a bare exception aborting the run or a NaN arriving as a null
    # the model will rationalize with a wrong story. ModelRetry is a pydantic-ai
    # concept, so this translation belongs here in the adapter, not in the
    # framework-neutral core or the intel layer.
    try:
        return binding.execute(**kwargs)
    except ValueError as exc:
        raise ModelRetry(str(exc)) from exc


@functools.lru_cache(maxsize=None)
def compile_tool(binding: ToolBinding) -> Callable[..., Any]:
    """
    Builds a real, introspectable function for one ToolBinding: an
    LLM safe signature (ids/primitives, RunContext[AgentDeps] first),
    whose body resolves domain fields and calls binding.execute(...).

    Generated via exec on real source text, not a **kwargs catch-all. This is
    because pydantic-ai derives the tool's JSON schema from the function's
    actual signature, so each of the ~20 bindings needs its own
    concrete parameter list. Same technique dataclasses uses internally
    to generate __init__, and the source is built entirely from our own
    ToolBinding data, never from external input.

    Parameters are emitted required first, then defaulted, each group keeping
    schema field order. Signature order is cosmetic here (the body calls
    binding.execute by keyword, and pydantic-ai reads names and requiredness,
    not position), so this costs nothing and means a schema whose defaulted
    field precedes a required one still compiles instead of dying in exec.

    Memoized (F-7): ToolBinding is frozen/hashable and the compiled output
    depends only on it, so every Assistant()/CapabilityAgent() construction
    re-running the exec codegen for the same ~20 bindings was pure waste, and
    the server multiplies that by every request. Cached for the process
    lifetime.
    """
    fields = dataclasses.fields(binding.input_schema)
    hints = typing.get_type_hints(binding.input_schema)

    namespace: dict[str, Any] = {
        "RunContext": RunContext,
        "AgentDeps": AgentDeps,
        "_binding": binding,
        "_resolve_field": resolve_field,
        "_execute": _execute_or_retry,
    }

    def has_default(f: "dataclasses.Field[Any]", fallback: Any = None) -> bool:
        # `fallback` is a resolver-supplied, LLM facing default (e.g. the
        # benchmark ticker), None meaning no default (see FieldResolver).
        return (
            f.default is not _MISSING
            or f.default_factory is not _MISSING  # type: ignore[misc]
            or fallback is not None
        )

    def param_source(
        param_name: str,
        type_key: str,
        f: "dataclasses.Field[Any]",
        fallback: Any = None,
    ) -> str:
        # The schema field's own default wins over the resolver's when both
        # exist, since the binding layer is closer to the math.
        if f.default is not _MISSING:
            namespace[f"_default_{param_name}"] = f.default
            return f"{param_name}: {type_key} = _default_{param_name}"
        if f.default_factory is not _MISSING:  # type: ignore[misc]
            namespace[f"_default_{param_name}"] = f.default_factory()
            return f"{param_name}: {type_key} = _default_{param_name}"
        if fallback is not None:
            namespace[f"_default_{param_name}"] = fallback
            return f"{param_name}: {type_key} = _default_{param_name}"
        return f"{param_name}: {type_key}"

    # Two buckets rather than one list, so required parameters can be emitted
    # ahead of defaulted ones regardless of schema field order. Python forbids
    # a required parameter after a defaulted one, and a RESOLVER default (see
    # FieldResolver) can make an early field optional while a later field stays
    # required, which the dataclass itself cannot catch: the schema looks fine
    # and the generated signature dies inside exec() as a bare SyntaxError.
    # Reordering is safe because the generated body calls binding.execute with
    # keyword arguments only, so parameter order carries no meaning, and
    # pydantic-ai derives the tool's JSON schema from names and requiredness,
    # not from position. Each bucket keeps schema order, so the result is
    # stable and predictable.
    required_params: list[str] = []
    optional_params: list[str] = []
    prep_lines: list[str] = []       # resolution hoisted to locals, named by finkritq field
    call_args: list[str] = []
    resolved_keys: list[str] = []    # finkritq field names of resolved domain objects
    defaulted_notes: list[str] = []  # resolver defaults applied, surfaced in the docstring

    def emit(param_name: str, type_key: str, f: "dataclasses.Field[Any]", fallback: Any = None) -> None:
        bucket = optional_params if has_default(f, fallback) else required_params
        bucket.append(param_source(param_name, type_key, f, fallback))

    for f in fields:
        if f.name in INJECTED_FIELDS:
            namespace[f"_inject_{f.name}"] = INJECTED_FIELDS[f.name]
            call_args.append(f"{f.name}=_inject_{f.name}(ctx.deps)")
            continue

        resolver = FIELD_RESOLVERS.get(f.name)
        if resolver is not None:
            pname = resolver.param_name
            namespace[f"_type_{pname}"] = resolver.param_type
            namespace[f"_resolver_{pname}"] = resolver
            emit(pname, f"_type_{pname}", f, fallback=resolver.default)
            if (
                f.default is _MISSING
                and f.default_factory is _MISSING  # type: ignore[misc]
                and resolver.default is not None
            ):
                defaulted_notes.append(f"{pname} defaults to {resolver.default!r} when omitted.")
            # Hoist resolution into a local named for the finkritq field, so an
            # output adapter can reference the resolved object (e.g. the portfolio).
            prep_lines.append(f"    {f.name} = _resolve_field(_resolver_{pname}, ctx.deps, {pname})")
            call_args.append(f"{f.name}={f.name}")
            resolved_keys.append(f.name)
        else:
            pname = f.name
            namespace[f"_type_{pname}"] = hints[f.name]
            emit(pname, f"_type_{pname}", f)
            call_args.append(f"{pname}={pname}")

    name = binding.contract.name
    params_src = ", ".join(
        ["ctx: RunContext[AgentDeps]", *required_params, *optional_params]
    )
    call_src = ", ".join(call_args)

    adapter = OUTPUT_ADAPTERS.get(name)
    if adapter is not None:
        # Adapter reshapes the raw finkritq result into a JSON-serializable
        # summary; return type becomes dict, not the binding's NDArray output.
        namespace["_adapt"] = adapter
        namespace["_return_type"] = dict
        resolved_dict = "{" + ", ".join(f"'{k}': {k}" for k in resolved_keys) + "}"
        body_lines = [
            *prep_lines,
            f"    _result = _execute(_binding, {call_src})",
            f"    return _adapt(_result, {resolved_dict})",
        ]
    else:
        namespace["_return_type"] = binding.output_schema
        body_lines = [*prep_lines, f"    return _execute(_binding, {call_src})"]

    source = f"def {name}({params_src}) -> _return_type:\n" + "\n".join(body_lines) + "\n"

    # dont_inherit=True: this module uses `from __future__ import annotations`,
    # which compile() otherwise silently inherits, stringifying every
    # annotation on the generated function instead of resolving real types.
    exec(
        compile(source, f"<finagent.adapter.compiler:{name}>", "exec", dont_inherit=True),
        namespace,
    )
    fn = namespace[name]
    # Resolver defaults are invisible in the contract description (the intel
    # layer does not know them), so name them here or the model asks the user
    # for a value the signature already supplies.
    fn.__doc__ = " ".join([binding.contract.description, *defaulted_notes])
    return fn


def compile_capability(
    capability: FinkritCapability,
    *,
    defer_loading: bool = False) -> PydanticCapability[AgentDeps]:
    return PydanticCapability(
        id=capability.name,
        description=capability.description,
        tools=[compile_tool(binding) for binding in capability.tools],
        defer_loading=defer_loading,
    )

