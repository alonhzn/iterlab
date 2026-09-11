"""iterlab — the GUI as a development environment for algorithms.

    iterlab demo          # from a shell
    iterlab.run("demo")   # from a script or an IDE

Both are the same path. Neither offers any way to build a layout in code: that
is drawn, never programmed (constitution Principle I).
"""

from .app import open_interface as _open_interface

#: Single source of truth for the version. `pyproject.toml` reads it from here,
#: so the two can never disagree.
__version__ = "1.5.0"

__all__ = ["run", "__version__"]


def run(name: str):
    """Open the interface called `name`.

    Creates it if it does not exist. Opens in editor mode when there is nothing
    to use yet, GUI mode when there is (FR-001a).
    """
    return _open_interface(name)
