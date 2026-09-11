"""Back an interface up when the iterlab that opens it is not the one that left it.

Every layout file records which iterlab last wrote it. When that differs from the
version now opening it — **in either direction** — both files are copied aside
before anything touches them:

    demo.yaml  ->  demo.yaml.v1.2.0.bak
    demo.py    ->  demo.py.v1.2.0.bak

The version in the name is the one that *wrote* the files, because that is what
the copy preserves.

Either direction matters, and the downgrade is the dangerous one. Opening a newer
file with an older build is the case where a key it has never heard of can be
dropped, or a type it does not know can be rejected outright. An upgrade is
safer, since migrations run forward and are tested — but a migration is still a
rewrite of the researcher's layout, and a copy costs nothing next to losing it.

The `.py` file is copied and never otherwise touched here. iterlab appends
handler stubs to it and renames handlers in it, and if either of those ever went
wrong across a version change, this is the copy that would matter most: the
layout can be redrawn, the algorithm cannot.

No GUI imports.
"""

from __future__ import annotations

import shutil
from pathlib import Path

#: What goes in the filename when the file has no stamp at all — every layout
#: written before this feature existed. Not a version number, and deliberately
#: not made to look like one.
UNKNOWN = "unknown"

SUFFIX = ".bak"


def backup_path(path, version: str) -> Path:
    """`demo.yaml` + `1.2.0` -> `demo.yaml.v1.2.0.bak`."""
    path = Path(path)
    return path.with_name(f"{path.name}.v{version or UNKNOWN}{SUFFIX}")


def needs_backup(recorded: str, current: str) -> bool:
    """Whether the file was last written by a different iterlab.

    Not a comparison of which is newer: any difference is a difference, and a
    downgrade is the one more likely to lose something.
    """
    return (recorded or "") != (current or "")


def back_up(interface, recorded: str):
    """Copy both files aside. Returns the paths written, in order.

    An existing backup for that version is left alone. If someone has moved
    between two versions more than once, the copy already on disk is the older
    and therefore more original of the two, and overwriting it with a later
    state would throw away exactly what this is for.

    Nothing here may raise. A directory that cannot be written to is a directory
    iterlab cannot damage either, so failing to copy is not a reason to refuse to
    open the interface - but it is a reason to say so, which the caller does.
    """
    written = []
    for path in (interface.layout_path, interface.code_path):
        source = Path(path)
        if not source.exists():
            continue
        target = backup_path(source, recorded)
        if target.exists():
            continue
        try:
            # copy2 keeps the timestamps, so the backup still says when that
            # version actually left it.
            shutil.copy2(source, target)
        except OSError:
            continue
        written.append(target)
    return written


def guard(interface, current: str):
    """Back the pair up if a different iterlab last wrote it.

    Returns (recorded_version, paths_written). An empty list means either that
    nothing needed doing or that the copies could not be made; the caller has
    the recorded version and can tell the difference.
    """
    recorded = getattr(interface.layout, "iterlab_version", "") or ""
    if not needs_backup(recorded, current):
        return recorded, []
    return recorded, back_up(interface, recorded)
