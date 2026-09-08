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

#: Room the editor needs beyond the interface itself: the sidebar and its
#: separator. The layout's own window size describes the *interface*, and is
#: advisory (data-model.md), so the editor may ask for more.
SIDEBAR_ALLOWANCE = 230

#: Floors for editor mode, so the palette and every property field fit without
#: scrolling on a first run. Tk unmaps children that do not fit rather than
#: clipping them, so an editor that is too small loses controls silently.
MIN_EDITOR_WIDTH = 1080
MIN_EDITOR_HEIGHT = 760

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

        from . import theme

        theme.apply_theme(self.root)
        self.root.title(f"iterlab — {interface.name}")
        self.root.geometry("{}x{}".format(*self._size_for(start_mode)))

        # Chrome lives outside the content frame so it survives every rebuild.
        self._chrome = self.tk.Frame(self.root, bg=theme.BG)
        self._chrome.pack(side="top", fill="x")
        self.tk.Frame(self.root, bg=theme.BORDER, height=1).pack(side="top", fill="x")

        self._content = self.tk.Frame(self.root, bg=theme.BG)
        self._content.pack(side="top", fill="both", expand=True)

        # Deferred import: modetoggle needs EDITOR/GUI from this module, and
        # importing it at module scope here would be circular. Same pattern as
        # _construct() below.
        from .session import Session

        #: Owned here, not by GUI mode, so it outlives every toggle. This is
        #: what makes a layout edit cost nothing but a rebuild of the widgets.
        self.session = Session()

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

    def _size_for(self, mode):
        """Window size for a mode, in pixels.

        GUI mode uses the interface's own size. Editor mode adds the sidebar
        and applies a floor, because the editor has controls of its own to fit
        and the interface may have been designed small.
        """
        window = self.interface.layout.window
        if mode != EDITOR:
            return window.width, window.height
        return (
            max(window.width + SIDEBAR_ALLOWANCE, MIN_EDITOR_WIDTH),
            max(window.height, MIN_EDITOR_HEIGHT),
        )

    def _grow_for_editor(self) -> None:
        """Enlarge the window if it is too small to edit in — never shrink it.

        Shrinking would discard a size the researcher chose deliberately, and
        switching modes should not rearrange their desktop.
        """
        self.root.update_idletasks()
        width, height = self._size_for(EDITOR)
        current_w = max(self.root.winfo_width(), 1)
        current_h = max(self.root.winfo_height(), 1)
        if current_w < width or current_h < height:
            self.root.geometry(f"{max(current_w, width)}x{max(current_h, height)}")

    def build(self, mode) -> None:
        """Build `mode` into the content frame, replacing whatever was there."""
        self.teardown()
        self.mode = mode
        if mode == EDITOR:
            self._grow_for_editor()
        self._built = self._construct(mode)

    def restart_session(self) -> None:
        """Throw the session away and start again in GUI mode.

        The one way to re-run `on_startup`, now that toggling preserves the
        session instead of discarding it.
        """
        self.session.restart()
        self.build(GUI)
        self._mode_toggle.refresh()

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
