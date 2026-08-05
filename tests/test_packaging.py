# tests/test_packaging.py
"""
Guards the finkrit wheel manifest.

finagent and finkritserver are bundled into the finkrit wheel through hatch's
force-include, which lists paths one by one because force-include ignores the
exclude rules that would otherwise keep tests out. That means a new top level
module is not packaged until someone remembers to add it here, and nothing fails
until an installed user imports it.

That is exactly how finkrit 0.1.1 shipped without finagent/logging_model.py,
which assistant.py imports unconditionally, so the installed command could not
start at all. A note in the manifest asking people to remember did not prevent
it. This test does, by failing in CI the moment a module exists on disk but not
in the manifest.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Source directory to the package name it is published under. Only top level
# modules are checked, subpackages are force-included whole as directories.
BUNDLED = {
    REPO_ROOT / "packages" / "finkritcore": "finkritcore",
    REPO_ROOT / "packages" / "finagent": "finagent",
    REPO_ROOT / "services" / "api" / "finkritserver": "finkritserver",
}


def _force_included() -> dict[str, str]:
    with PYPROJECT.open("rb") as handle:
        config = tomllib.load(handle)
    return config["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]


def _top_level_modules(package_dir: Path) -> set[str]:
    return {
        path.name
        for path in package_dir.glob("*.py")
        if not path.name.startswith("_test")
    }


@pytest.mark.parametrize("package_dir,dist_name", BUNDLED.items(), ids=lambda v: str(v))
def test_every_top_level_module_is_packaged(package_dir: Path, dist_name: str):
    included = _force_included()
    packaged = {
        Path(source).name
        for source in included
        if source.startswith(str(package_dir.relative_to(REPO_ROOT)))
    }

    missing = sorted(_top_level_modules(package_dir) - packaged)
    assert not missing, (
        f"{dist_name} modules exist on disk but are not in the wheel manifest: "
        f"{', '.join(missing)}. Add them to [tool.hatch.build.targets.wheel.force-include] "
        f"in pyproject.toml, otherwise pip install finkrit ships without them."
    )


@pytest.mark.parametrize("package_dir,dist_name", BUNDLED.items(), ids=lambda v: str(v))
def test_every_subpackage_is_packaged(package_dir: Path, dist_name: str):
    # Subpackages (adapter, agent, report, store) are included as whole
    # directories. A new one is just as easy to forget as a module.
    included = _force_included()
    packaged = {Path(source).name for source in included}

    on_disk = {
        path.name
        for path in package_dir.iterdir()
        if path.is_dir()
        and (path / "__init__.py").exists()
        and path.name not in {"tests", "__pycache__"}
    }

    missing = sorted(on_disk - packaged)
    assert not missing, (
        f"{dist_name} subpackages are not in the wheel manifest: {', '.join(missing)}."
    )


def test_the_example_portfolio_is_packaged():
    # `finkrit cli --file example` reads this out of the installed package. It is
    # data rather than a module, so the two guards above cannot see it, and a
    # missing file surfaces only when a new user runs the one command the README
    # tells them to run first.
    included = _force_included()
    assert "packages/finagent/examples" in included, (
        "the bundled example portfolio is not in the wheel manifest, so "
        "`finkrit cli --file example` would fail on a pip install"
    )
    assert (REPO_ROOT / "packages" / "finagent" / "examples" / "portfolio.csv").is_file()


def test_tests_are_not_packaged():
    # The reason the manifest enumerates instead of including the package whole.
    included = _force_included()
    assert not [source for source in included if "tests" in Path(source).parts]
