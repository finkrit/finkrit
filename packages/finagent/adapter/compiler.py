# finagent/adapter/compiler.py

from __future__ import annotations

import dataclasses
import typing
from typing import Any, Callable

from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability as PydanticCapability

from finkritintel.capability.base import Capability as FinkritCapability
from finkritintel.tool.binding import ToolBinding

from finagent.adapter.output import OUTPUT_ADAPTERS
from finagent.adapter.resolve import FIELD_RESOLVERS, INJECTED_FIELDS, resolve_field
from finagent.deps import AgentDeps

_MISSING = dataclasses.MISSING


def compile_tool(binding: ToolBinding) -> Callable[..., Any]:
    """
    Builds a real, introspectable function for one ToolBinding: an
    LLM-safe signature (ids/primitives, RunContext[AgentDeps] first),
    whose body resolves domain fields and calls binding.execute(...).

    Generated via exec on real source text, not a **kwargs catch-all --
    pydantic-ai derives the tool's JSON schema from the function's
    actual signature, so each of the ~20 bindings needs its own
    concrete parameter list. Same technique dataclasses uses internally
    to generate __init__; the source is built entirely from our own
    ToolBinding data, never from external input.
    """
    fields = dataclasses.fields(binding.input_schema)
    hints = typing.get_type_hints(binding.input_schema)

    namespace: dict[str, Any] = {
        "RunContext": RunContext,
        "AgentDeps": AgentDeps,
        "_binding": binding,
        "_resolve_field": resolve_field,
    }

    def param_source(param_name: str, type_key: str, f: "dataclasses.Field[Any]") -> str:
        if f.default is not _MISSING:
            namespace[f"_default_{param_name}"] = f.default
            return f"{param_name}: {type_key} = _default_{param_name}"
        if f.default_factory is not _MISSING:  # type: ignore[misc]
            namespace[f"_default_{param_name}"] = f.default_factory()
            return f"{param_name}: {type_key} = _default_{param_name}"
        return f"{param_name}: {type_key}"

    param_defs: list[str] = []
    prep_lines: list[str] = []       # resolution hoisted to locals, named by finkritq field
    call_args: list[str] = []
    resolved_keys: list[str] = []    # finkritq field names of resolved domain objects

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
            param_defs.append(param_source(pname, f"_type_{pname}", f))
            # Hoist resolution into a local named for the finkritq field, so an
            # output adapter can reference the resolved object (e.g. the portfolio).
            prep_lines.append(f"    {f.name} = _resolve_field(_resolver_{pname}, ctx.deps, {pname})")
            call_args.append(f"{f.name}={f.name}")
            resolved_keys.append(f.name)
        else:
            pname = f.name
            namespace[f"_type_{pname}"] = hints[f.name]
            param_defs.append(param_source(pname, f"_type_{pname}", f))
            call_args.append(f"{pname}={pname}")

    name = binding.contract.name
    params_src = ", ".join(["ctx: RunContext[AgentDeps]", *param_defs])
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
            f"    _result = _binding.execute({call_src})",
            f"    return _adapt(_result, {resolved_dict})",
        ]
    else:
        namespace["_return_type"] = binding.output_schema
        body_lines = [*prep_lines, f"    return _binding.execute({call_src})"]

    source = f"def {name}({params_src}) -> _return_type:\n" + "\n".join(body_lines) + "\n"

    # dont_inherit=True: this module uses `from __future__ import annotations`,
    # which compile() otherwise silently inherits, stringifying every
    # annotation on the generated function instead of resolving real types.
    exec(
        compile(source, f"<finagent.adapter.compiler:{name}>", "exec", dont_inherit=True),
        namespace,
    )
    fn = namespace[name]
    fn.__doc__ = binding.contract.description
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

