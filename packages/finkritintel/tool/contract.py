# finkritintel/tool/contract.py

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolContract:
    """
    The intelligence-facing abstraction: what a tool *is* (name, description,
    category, tags), decoupled from its schema/implementation so those can
    change without touching the contract.

    ``category`` (coarse, e.g. "risk") and ``tags`` (fine, e.g. "portfolio",
    "volatility") are metadata for discovery/prompting; ``tags`` also drives
    asset-vs-portfolio dispatch within a domain capability.
    """

    name: str
    description: str
    category: str
    tags: tuple[str, ...] = ()

