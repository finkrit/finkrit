# finkritintel/capability/base.py

from dataclasses import dataclass, field

from finkritintel.tool.binding import ToolBinding


@dataclass(frozen=True, slots=True)
class Capability:
    """
    A named group of tool bindings an agent exposes as one unit.

    Invariants (enforced here rather than left to each consumer's tests): a
    capability needs a non-empty name and description, and no two of its tools
    may share a contract name to prevent collision as required by agent framework
    which registers tools by name.
    """

    name: str
    description: str
    tools: tuple[ToolBinding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Capability requires a non-empty name.")
        if not self.description:
            raise ValueError("Capability requires a non-empty description.")

        names = [tool.contract.name for tool in self.tools]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate tool contract name(s) in capability '{self.name}': "
                f"{', '.join(sorted(duplicates))}."
            )

