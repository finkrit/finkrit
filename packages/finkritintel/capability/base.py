from dataclasses import dataclass

from packages.finkritintel.tool.binding import ToolBinding


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    description: str
    tools: tuple[ToolBinding, ...]

