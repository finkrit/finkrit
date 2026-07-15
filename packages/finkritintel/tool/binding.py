# finkritintel/tool/binding.py

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from packages.finkritintel.tool.contract import ToolContract


@dataclass(frozen=True, slots=True)
class ToolBinding:
    """
    The execution-facing abstraction.

    Pairs a ToolContract with a concrete implementation and its schemas.
    Schemas live here because they are tied to the provider, not the contract.
    Developers can call binding.execute(...) directly.
    An agent can inspect binding.contract to discover name and description,
    and binding.input_schema / binding.output_schema for the call signature.
    """

    contract: ToolContract
    input_schema: type
    output_schema: type
    implementation: Callable[..., Any]

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self.implementation(*args, **kwargs)


