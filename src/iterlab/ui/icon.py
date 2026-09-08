"""Putting the iterlab icon on the window.

Tk's default is the Tcl feather, which tells a researcher nothing and looks
like a stray interpreter window in a taskbar full of real applications.

Applied through both mechanisms, because neither covers everything: `iconphoto`
is the portable one and is what X11 and macOS honour, while `iconbitmap` with a
real `.ico` is what Windows uses for the title bar and taskbar, and it is
noticeably crisper there.

An icon is decoration. Nothing here may raise: a missing file or a window
manager with opinions is not a reason to lose the session (Principle III).
"""

from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICO = ASSETS / "iterlab.ico"
PNG = ASSETS / "iterlab.png"

#: Tk garbage-collects a PhotoImage the moment the last reference goes, and a
#: collected icon silently reverts to the feather. Held for the process.
_keep = []


def apply(root) -> bool:
    """Set the window icon. Returns whether anything was applied."""
    applied = False

    if PNG.exists():
        try:
            import tkinter as tk

            photo = tk.PhotoImage(master=root, file=str(PNG))
            # True: inherited by every toplevel this app opens, so a dialog or
            # a tooltip window never shows the default instead.
            root.iconphoto(True, photo)
            _keep.append(photo)
            applied = True
        except Exception:
            pass

    if ICO.exists():
        try:
            # Windows-only; a no-op or an error elsewhere, hence its own guard.
            root.iconbitmap(default=str(ICO))
            applied = True
        except Exception:
            pass

    return applied
