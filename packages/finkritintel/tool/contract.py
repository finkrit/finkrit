# finkritintel/tool/contract.py 

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolContract:
    """
    The intelligence-facing abstraction.

    Describes what a tool is: its name, description, and category.
    We want to decouple this from schema since the implementation might change.
    Category enables self-classifying contracts for discovery and prompting.
    """

    name: str
    description: str
    category: str
    summary: str | None = None
    tags: tuple[str, ...] = ()

