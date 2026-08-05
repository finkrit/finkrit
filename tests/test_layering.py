# tests/test_layering.py
"""
Import-direction guards for the package DAG.

``x -> y`` means x imports y. The legal edges are:

    finkritserver -> finkritcore, finagent
    finagent      -> finkritcore, finkritintel
    finkritcore   -> finkritintel, finkritq
    finkritintel  -> finkritq

What this pins is the direction that must never appear: a lower layer reaching
up. The one that matters most is finkritcore importing the agent framework.
finkritcore's whole promise is that the dashboard, the reports, and a labelled
CSV upload work with no model and no key, and a single stray ``import
pydantic_ai`` silently converts the deterministic layer into an agentic one.
Nothing would fail, the tests would still pass, and the property would just be
gone. A rule that lives in a document is a wish. This makes it a failure.

Note that finagent -> finkritcore and finagent -> finkritintel are parallel
edges, not a chain. finagent binds intel's capabilities directly (that is what
a framework-neutral contract layer is for) and uses core for one thing at
runtime: resolving an opaque portfolio id into a Portfolio through the Store.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Package source directory -> module prefixes it must never import.
#
# Tests are excluded from the scan: they may import upward freely, and do
# (finagent's tests use core's fixtures). The rule protects shipped code, which
# is the only code an installed user runs.
FORBIDDEN = {
    "packages/finkritq": (
        "pydantic_ai", "finkritintel", "finkritcore", "finagent", "finkritserver", "finkrit",
    ),
    "packages/finkritintel": (
        "pydantic_ai", "finkritcore", "finagent", "finkritserver", "finkrit",
    ),
    "packages/finkritcore": (
        "pydantic_ai", "finagent", "finkritserver", "finkrit",
    ),
    "packages/finagent": ("finkritserver",),
}

_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)|import\s+([\w.]+))", re.MULTILINE)


def _imported_modules(path: Path) -> set[str]:
    return {
        match.group(1) or match.group(2)
        for match in _IMPORT.finditer(path.read_text())
    }


def _source_files(package_dir: Path) -> list[Path]:
    return [
        path
        for path in package_dir.rglob("*.py")
        if "tests" not in path.parts and "__pycache__" not in path.parts
    ]


def _violates(module: str, banned: str) -> bool:
    # Exact name or a dotted child of it. Never a string prefix, or banning
    # "finkrit" would also ban finkritq, finkritintel, and finkritcore.
    return module == banned or module.startswith(banned + ".")


@pytest.mark.parametrize("package,banned", sorted(FORBIDDEN.items()))
def test_no_upward_imports(package: str, banned: tuple[str, ...]):
    violations = [
        f"{path.relative_to(REPO_ROOT)}: imports {module}"
        for path in _source_files(REPO_ROOT / package)
        for module in _imported_modules(path)
        for name in banned
        if _violates(module, name)
    ]
    assert not violations, (
        f"{package} breaks the layer DAG:\n  " + "\n  ".join(sorted(violations))
    )


def test_the_sibling_packages_are_not_confused_for_each_other():
    # The matching above is exact-or-dotted-child on purpose. If it ever
    # regresses to a plain startswith, banning "finkrit" takes finkritq,
    # finkritintel, and finkritcore down with it and every layer looks clean
    # because nothing is left to import.
    assert _violates("finkrit.web", "finkrit")
    assert _violates("finkrit", "finkrit")
    assert not _violates("finkritq", "finkrit")
    assert not _violates("finkritcore.store", "finkrit")


def test_finkritcore_is_free_of_the_agent_framework():
    # Stated separately from the parametrized sweep because this is the edge
    # the package exists to hold: no LLM anywhere in a finkritcore install.
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in _source_files(REPO_ROOT / "packages" / "finkritcore")
        if any(m == "pydantic_ai" or m.startswith("pydantic_ai.") for m in _imported_modules(path))
    ]
    assert not offenders, f"finkritcore imports pydantic_ai in: {offenders}"
