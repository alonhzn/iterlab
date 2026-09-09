"""What a file or folder selector chose last time.

A selection has to outlive the process, not just the session: a researcher who
picked a data directory yesterday should not pick it again today. So it goes to
disk — but **not** into the layout file. `demo.yaml` describes the interface, and
writing a runtime choice into it would make it a log of what happened instead
(Principle II), and would show up as a spurious diff in everyone's repository.

It goes to the user's own state directory instead, keyed by the absolute path of
the interface. That keeps the project folder as the two files it has always
been. The cost, accepted deliberately: moving or copying a project loses its
memory and it starts fresh — which behaves exactly like a first run, so nothing
breaks, it merely forgets.

Nothing here can raise on the researcher's account. A missing file, unreadable
JSON, a directory that cannot be created, a read-only disk: all of them mean
"nothing remembered", which is a state the caller must handle anyway because it
is what every first run looks like.

No GUI imports.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

FILENAME = "selections.json"


def state_dir() -> Path:
    """Where this platform keeps small per-user state.

    Not a config directory: these are choices the program made on the
    researcher's behalf, not settings they wrote.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "iterlab"


def state_file() -> Path:
    return state_dir() / FILENAME


def _key(interface_path) -> str:
    """One interface, identified by where it lives.

    Resolved so that the same interface reached by a different relative path is
    the same key, and lower-cased on Windows where paths are case-insensitive
    and the same file can be spelled several ways.
    """
    resolved = str(Path(interface_path).resolve())
    return resolved.lower() if sys.platform == "win32" else resolved


def _load_all() -> dict:
    try:
        raw = json.loads(state_file().read_text(encoding="utf-8"))
    except Exception:
        # Missing, empty, or corrupt - all mean the same thing to a caller, and
        # none of them is worth a fault. The next write repairs the file.
        return {}
    return raw if isinstance(raw, dict) else {}


def load(interface_path) -> dict:
    """Every remembered selection for one interface, as {tag: path}."""
    entry = _load_all().get(_key(interface_path))
    if not isinstance(entry, dict):
        return {}
    return {t: p for t, p in entry.items() if isinstance(t, str) and isinstance(p, str)}


def remember(interface_path, tag, selection) -> bool:
    """Record one selection. Returns whether it reached the disk."""
    everything = _load_all()
    key = _key(interface_path)
    entry = everything.get(key)
    if not isinstance(entry, dict):
        entry = {}
    entry[str(tag)] = str(selection)
    everything[key] = entry

    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        # The same temp-file-and-replace used for the researcher's own files, so
        # an interrupted write cannot leave a half-written file behind.
        from ..codegen.templates import atomic_write

        atomic_write(state_file(), json.dumps(everything, indent=2, sort_keys=True))
        return True
    except Exception:
        # A read-only disk or a locked profile costs the researcher the memory,
        # never the session.
        return False


def forget(interface_path, tag=None) -> bool:
    """Drop one remembered selection, or all of an interface's."""
    everything = _load_all()
    key = _key(interface_path)
    if key not in everything:
        return True
    if tag is None:
        everything.pop(key, None)
    else:
        entry = everything.get(key)
        if isinstance(entry, dict):
            entry.pop(str(tag), None)
        if not entry:
            everything.pop(key, None)

    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        from ..codegen.templates import atomic_write

        atomic_write(state_file(), json.dumps(everything, indent=2, sort_keys=True))
        return True
    except Exception:
        return False


def usable(selection, *, expect_dir=False) -> bool:
    """Whether a remembered path is still something worth offering back."""
    if not selection:
        return False
    try:
        path = Path(selection)
        return path.is_dir() if expect_dir else path.is_file()
    except OSError:
        # A path the OS cannot even evaluate - a dead network drive, say.
        return False


def starting_directory(selection, *, expect_dir=False) -> str:
    """Where the dialog should open.

    The remembered target if it is still there; the folder that held it if only
    the file has gone, since a renamed file is usually still next to where it
    was; and otherwise the working directory, which is where a first run starts.
    """
    if usable(selection, expect_dir=expect_dir):
        return str(Path(selection))
    if selection:
        try:
            parent = Path(selection).parent
            if parent.is_dir():
                return str(parent)
        except OSError:
            pass
    return os.getcwd()
