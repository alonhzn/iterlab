"""Putting the iterlab icon on the window.

Tk's default is a blank placeholder, which tells a researcher nothing and looks
like a stray interpreter window in a taskbar full of real applications.

**Exactly one mechanism is applied, never both.** Tk offers two — `iconbitmap`
with a real `.ico`, and `iconphoto` with a `PhotoImage` — and each works on its
own. Applying both to the same window does not layer them: the icon comes out a
blank grey square, which is worse than either and worse than doing nothing. An
earlier version here called both "for coverage" and that is precisely what it
produced.

Which one depends on the platform, and neither is a fallback for a *working*
call:

* Windows takes `iconbitmap`, because a real `.ico` carries a frame drawn for
  each size. The title bar then gets the 16 px artwork rather than Tk squeezing
  down the 256.
* Everywhere else takes `iconphoto`, which is what X11 and macOS honour.

An icon is decoration. Nothing here may raise: a missing file, or a window
manager with opinions, is not a reason to lose the session (Principle III).
"""

from __future__ import annotations

import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICO = ASSETS / "iterlab.ico"
PNG = ASSETS / "iterlab.png"

#: Tk garbage-collects a PhotoImage the moment the last reference goes, and a
#: collected icon silently reverts to the default. Held for the process.
_keep = []


def _apply_bitmap(root) -> bool:
    """Windows: the `.ico`, so each size gets the frame drawn for it."""
    if not ICO.exists():
        return False
    try:
        # `default` also gives it to every toplevel opened later, so a dialog
        # never shows the placeholder instead.
        root.iconbitmap(default=str(ICO))
        return True
    except Exception:
        return False


def _apply_photo(root) -> bool:
    """Everywhere else: the PNG, through Tk's portable mechanism."""
    if not PNG.exists():
        return False
    try:
        import tkinter as tk

        photo = tk.PhotoImage(master=root, file=str(PNG))
        root.iconphoto(True, photo)
        _keep.append(photo)
        return True
    except Exception:
        return False


def apply(root) -> bool:
    """Set the window icon by whichever single mechanism suits this platform.

    Returns whether one was applied. The other is tried only when the first
    could not be — a failure, not a supplement.
    """
    if sys.platform == "win32":
        return _apply_bitmap(root) or _apply_photo(root)
    return _apply_photo(root) or _apply_bitmap(root)
