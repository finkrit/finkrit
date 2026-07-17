# finagent/adapter/__init__.py
"""
finagent.adapter — the translation machinery between finkritintel and pydantic-ai.

The core problem this package solves: a finkritintel ``ToolBinding`` expects
real domain objects (``Portfolio``, ``Asset``, ``DataRegistry``), but an LLM
can only ever supply primitives (a portfolio id, a ticker) as JSON tool-call
arguments. So each exposed tool needs an LLM-safe signature AND a way to turn
those ids back into objects before calling finkritintel.

  - ``resolve`` — the id -> object mapping. ``FIELD_RESOLVERS`` maps a
    finkritintel schema field name (``portfolio``, ``asset``, ``benchmark``)
    to the LLM-facing primitive param and a resolver that looks the object up
    in the ``Store``. ``INJECTED_FIELDS`` covers things supplied from deps and
    never shown to the LLM (the ``registry``). Store misses become
    ``pydantic_ai.ModelRetry`` so the model can recover instead of crashing.

  - ``compiler`` — ``compile_tool`` generates a real, introspectable function
    per binding via ``exec`` on source text (pydantic-ai derives each tool's
    JSON schema from the actual signature, so a ``**kwargs`` catch-all won't
    do). ``compile_capability`` bundles the compiled tools into one
    ``pydantic_ai.capabilities.Capability``. Adding a new finkritintel
    capability requires zero new code here.

  - ``output`` — ``OUTPUT_ADAPTERS`` reshape the raw ``NDArray`` returns of a
    few tools (drawdown series, risk contributions) into JSON-serializable
    summaries at the agent edge only (finkritq still returns full arrays for
    non-agent callers). Without this those tools crash tool-return
    serialization.
"""

from .compiler import compile_capability, compile_tool
from .output import OUTPUT_ADAPTERS
from .resolve import FIELD_RESOLVERS, INJECTED_FIELDS, FieldResolver

__all__ = [
    "compile_capability",
    "compile_tool",
    "FieldResolver",
    "FIELD_RESOLVERS",
    "INJECTED_FIELDS",
    "OUTPUT_ADAPTERS",
]
