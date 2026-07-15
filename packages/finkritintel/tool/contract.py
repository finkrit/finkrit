# finkritintel/tool/contract.py 

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolContract:
    """
    The intelligence-facing abstraction.

    Describes what a tool is: its name and description.
    We want to decouple this from schema since the implementation might change
    """

    name: str
    description: str
    summary: str | None = None

