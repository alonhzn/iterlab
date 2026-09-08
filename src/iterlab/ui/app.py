"""The single Tk root, and ownership of which mode is currently built.

One root lives for the whole process. A mode switch destroys every content
widget and builds the other mode's in its place; the root, the window geometry
and the mode toggle survive (research.md R13).

Rebuilding rather than hiding is deliberate. Hidden widgets keep live bindings
that still fire, and this architecture exists to make behavior inspectable. It
also gives the session semantics for free: discarding GUI-mode widgets discards
the `ev` that holds them (FR-015d), and rebuilding creates a fresh one (FR-015e).
"""

from __future__ import annotations

EDITOR = "editor"
GUI = "gui"

_TK_MISSING_MESSAGE = """\
iterlab needs tkinter, which is missing from this Python installation.

tkinter ships with Python on Windows and macOS, but is packaged separately on
several Linux distributions and cannot be installed from PyPI.

  Debian / Ubuntu :  sudo apt install python3-tk
  Fedora / RHEL   :  sudo dnf install python3-tkinter
  Arch            :  sudo pacman -S tk
"""


class TkinterMissing(Exception):
    """Raised instead of a bare ImportError, so the message is actionable."""

    def __init__(self):
        super().__init__(_TK_MISSING_MESSAGE)


def require_tkinter():
    """Import tkinter, or raise something a researcher can act on (R12)."""
    try:
        import tkinter
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise TkinterMissing() from exc
    return tkinter


class App:
    """Owns the root window and the current mode."""

    def __init__(self, interface, start_mode=EDITOR, root=None):
        self.tk = require_tkinter()
        self.interface = interface
        self.mode = start_mode
        self._content = None
        self._built = None
        self._owns_root = root is None

        self.root = root if root is not None else self.tk.Tk()
        self.root.title(f"iterlab — {interface.name}")
        self.root.geometry(f"{interface.layout.window.width}x{interface.layout.window.height}")

        # Chrome lives outside the content frame so it survives every rebuild.
        self._chrome = self.tk.Frame(self.root)
        self._chrome.pack(side="top", fill="x")

        self._content = self.tk.Frame(self.root)
        self._content.pack(side="top", fill="both", expand=True)

        # Deferred import: modetoggle needs EDITOR/GUI from this module, and
        # importing it at module scope here would be circular. Same pattern as
        # _construct() below.
        from .modetoggle import ModeToggle

        self._mode_toggle = ModeToggle(self)

    # -- mode lifecycle --------------------------------------------------

    @property
    def content(self):
        return self._content

    @property
    def chrome(self):
        return self._chrome

    def teardown(self) -> None:
        """Destroy everything the current mode built.

        Anything the mode owned — including a GUI-mode `ev` — goes with it.
        """
        if self._built is not None and hasattr(self._built, "teardown"):
            self._built.teardown()
        for child in self._content.winfo_children():
            child.destroy()
        self._built = None

    def build(self, mode) -> None:
        """Build `mode` into the content frame, replacing whatever was there."""
        self.teardown()
        self.mode = mode
        self._built = self._construct(mode)

    def toggle(self) -> str:
        """Switch modes. The whole of FR-015 is this method."""
        self.build(GUI if self.mode == EDITOR else EDITOR)
        self._mode_toggle.refresh()
        return self.mode

    def _construct(self, mode):
        # Imported here rather than at module scope: designer and runner both
        # import this module, and importing them eagerly would be circular.
        if mode == EDITOR:
            from .designer import Designer

            return Designer(self)
        from .runner import Runner

        return Runner(self)

    @property
    def built(self):
        return self._built

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        """Tear the mode down, and the window too if this App made it."""
        self.teardown()
        for frame in (self._content, self._chrome):
            if frame is not None:
                frame.destroy()
        if self._owns_root:
            self.root.destroy()
