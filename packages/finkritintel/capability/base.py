# finkritintel/capability/base.py

from dataclasses import dataclass, field

from finkritintel.tool.binding import ToolBinding


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    description: str
    tools: tuple[ToolBinding, ...] = field(default_factory=tuple)

