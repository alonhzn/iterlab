"""The operating system's file and folder choosers, behind one seam.

These are the only modal dialogs iterlab opens, and they exist because a file
chooser is one thing a researcher should not have to build or be given a
substitute for: the OS one is the one they already know, with their places, their
recent folders and their network drives in it.

Everything goes through the two functions here so that there is a single place
to replace them. That matters more than it looks:

* The test suite refuses modal dialogs outright (`tests/conftest.py`), because a
  suite that stops for a human is not a release gate. Tests replace *these*
  functions; the ban on `tkinter.filedialog` stays exactly as it is, so any code
  path that reaches a real dialog without being replaced fails loudly instead of
  hanging.
* A cancelled dialog and a chosen path come back in one shape — `""` or a path —
  rather than Tk's mix of `""`, `()` and `None` depending on platform and
  which chooser was used.

Returning `""` for cancel is deliberate: the caller then treats "cancelled" and
"nothing chosen yet" identically, which is what the interface should do anyway.
"""

from __future__ import annotations

ALL_FILES = ("All files", "*.*")


def filetypes_for(extensions):
    """Tk `filetypes` for a parsed extension tuple.

    "All files" is always offered last. A filter the researcher cannot escape
    would be a trap: the one file they need is always the one that was saved
    with the wrong suffix.
    """
    if not extensions:
        return [ALL_FILES]
    patterns = " ".join(f"*.{e}" for e in extensions)
    listed = ", ".join(f".{e}" for e in extensions)
    return [(f"Supported files ({listed})", patterns), ALL_FILES]


def _clean(result) -> str:
    """Tk answers a cancel as "", () or None depending on where you asked."""
    if not result:
        return ""
    return str(result)


def ask_open_file(parent=None, initial_dir=None, extensions=()) -> str:
    """Open the OS file chooser. Returns the path, or "" if cancelled."""
    from tkinter import filedialog

    return _clean(
        filedialog.askopenfilename(
            parent=parent,
            initialdir=initial_dir or None,
            filetypes=filetypes_for(extensions),
        )
    )


def ask_directory(parent=None, initial_dir=None) -> str:
    """Open the OS folder chooser. Returns the path, or "" if cancelled."""
    from tkinter import filedialog

    return _clean(
        filedialog.askdirectory(
            parent=parent,
            initialdir=initial_dir or None,
            mustexist=True,
        )
    )
