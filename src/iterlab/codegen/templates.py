"""The text iterlab generates into the researcher's file.

The *signature* of a generated stub is public surface (contracts/handler-api.md);
the comment wording is not, and may be reworded in a PATCH.

No GUI imports.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

STARTER_FILE = '''"""{name} — an iterlab interface.

Open it:  iterlab {name}
Switch between editing and using it with the toggle in the top-left corner.
"""


def on_startup(ev):
    # Runs once when the interface opens, before anything else.
    #
    # Load your data HERE, not at the top of this file. Anything at module level
    # re-runs when iterlab picks up an edit; anything in here does not.
    pass
'''

_BUTTON_STUB = '''

def on_clicked_{name}(ev, event):
    # Runs when you click {name}.
    # Delete this function if you don't need it — nothing will break.
    print(f"{name} clicked with the {{event.button}} button")
'''

_PLOT_STUB = '''

def on_clicked_{name}(ev, event):
    # Runs when you click inside {name}.
    # event.x and event.y are in the plot's own data coordinates, not pixels.
    # Delete this function if you don't need it — nothing will break.
    print(f"{name} clicked at ({{event.x}}, {{event.y}})")
'''

_STUBS = {"button": _BUTTON_STUB, "plot_area": _PLOT_STUB}


def starter_file(name: str) -> str:
    return STARTER_FILE.format(name=name)


def default_stub(element) -> str:
    """The single stub generated when an element is created (FR-017d).

    Stubs for the other interactions are never generated; the researcher writes
    those when they want them.
    """
    try:
        template = _STUBS[element.type]
    except KeyError:  # pragma: no cover - closed set, guarded by schema
        raise NotImplementedError(f"no stub template for {element.type!r}") from None
    return template.format(name=element.name)


CRLF = "\r\n"
LF = "\n"


def read_source(path) -> str:
    """Read the researcher's file with its line endings intact.

    `Path.read_text` translates every CRLF to LF in memory. Writing that back
    rewrites every line of a file written by a Windows editor — a whole-file
    diff caused by adding one element, which is precisely what Principle V
    forbids.
    """
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def detect_newline(source: str) -> str:
    """The file's own line ending, so appended text matches what is there."""
    return CRLF if CRLF in source else LF


def atomic_write(path, text: str) -> None:
    """Write via a temp file in the same directory, then replace.

    `os.replace` is atomic on POSIX and Windows alike. An interruption leaves the
    previous contents intact rather than a truncated file — the prior spike wrote
    through an open read-write handle and could corrupt the researcher's code
    (constitution Principle V, FR-013).

    `newline=""` disables translation, so whatever line endings `text` carries
    reach the disk unchanged.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_starter_file(path, name: str) -> None:
    atomic_write(path, starter_file(name))
