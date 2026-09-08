"""The package's public surface actually exists.

Written because the same defect has now appeared four times: a component fully
implemented and never connected to anything. `iterlab.run` was documented in
contracts/commands.md and in the README while `__init__.py` was empty, so every
test passed and the documented entry point did not exist.

These assert the surface a researcher touches, not the internals behind it.
"""

import importlib.metadata

import pytest

import iterlab


def test_run_is_importable_and_callable():
    """contracts/commands.md promises `from iterlab import run`."""
    from iterlab import run

    assert callable(run)


def test_version_is_exposed():
    assert isinstance(iterlab.__version__, str)
    assert iterlab.__version__.count(".") == 2, "expected MAJOR.MINOR.PATCH"


def test_declared_version_matches_installed_metadata():
    """One source of truth: pyproject reads the version from __init__.py.

    If these drift, a released wheel claims a version the code does not.
    """
    assert importlib.metadata.version("iterlab") == iterlab.__version__


def test_console_script_entry_point_resolves():
    """`iterlab = iterlab.cli:main` must point at something that exists."""
    scripts = importlib.metadata.entry_points(group="console_scripts")
    entry = next((e for e in scripts if e.name == "iterlab"), None)
    assert entry is not None, "the iterlab console script is not registered"
    assert callable(entry.load())


def test_no_layout_building_api_is_exposed():
    """Principle I: layout is drawn, never programmed.

    A public helper for constructing elements in code would be the start of the
    drift the principle exists to prevent.
    """
    public = {n for n in dir(iterlab) if not n.startswith("_")}
    for forbidden in ("Element", "Layout", "Rect", "add_element", "create_element"):
        assert forbidden not in public, f"iterlab.{forbidden} must not be public"
