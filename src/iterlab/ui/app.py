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

#: Room the editor needs beyond the interface itself: the toolbar and the hair
#: line beside it. Added to the interface size rather than eating into it, so
#: the canvas is *exactly* the window the researcher will run in - the same
#: pixels, not merely the same proportions.
SIDEBAR_ALLOWANCE = 211
TOOLBAR_ALLOWANCE = 87

#: How long to wait after a resize before writing it down. Dragging a window
#: edge fires <Configure> continuously, and saving on every pixel would rewrite
#: the layout file hundreds of times for one drag.
RESIZE_SAVE_MS = 400

#: The hair line under the top bar.
SEPARATOR_HEIGHT = 1

#: A floor on the interface itself. Small enough that a compact dialog is still
#: expressible; large enough that the window is not a sliver nobody can grab.
MIN_INTERFACE_WIDTH = 320
MIN_INTERFACE_HEIGHT = 240

#: The editor window is never shorter than this, whatever the interface is.
#:
#: Not a floor on the *interface* — that is what made the two modes different
#: shapes before. The canvas stays exactly the interface's size and the leftover
#: height is dead space below it. Without this, an 800x450 interface gave the
#: toolbar 402 px for 596 px of controls, and the property fields fell off the
#: bottom of the window where nothing could reach them.
MIN_EDITOR_HEIGHT = 660

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

        from . import icon

        icon.apply(self.root)

        # Chrome lives outside the content frame so it survives every rebuild.
        self._chrome = self.tk.Frame(self.root, bg=theme.BG)
        self._chrome.pack(side="top", fill="x")
        self.tk.Frame(
            self.root, bg=theme.BORDER, height=SEPARATOR_HEIGHT
        ).pack(side="top", fill="x")

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

        # Sized only now: the window is the interface area plus this top bar,
        # so the bar has to exist before its height can be asked for.
        self.root.geometry("{}x{}".format(*self._size_for(start_mode)))

        self._resize_save = None
        #: True while a mode switch is resizing the window itself. A resize we
        #: performed is not the researcher choosing a size, and a debounced save
        #: firing in the gap between changing mode and Tk applying the new
        #: geometry would record the *other* mode's width as the interface size.
        self._switching = False
        self.root.bind("<Configure>", self._on_configure)

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
        if self._resize_save is not None:
            # Save now rather than losing a resize made just before a switch.
            self._cancel_resize_save()
            self.remember_size()
        if self._built is not None and hasattr(self._built, "teardown"):
            self._built.teardown()
        for child in self._content.winfo_children():
            child.destroy()
        self._built = None

    # -- remembering the size --------------------------------------------

    def _on_configure(self, event):
        """A resize, possibly one of hundreds in a single drag."""
        if self._switching:
            return
        if event.widget is not self.root:
            # <Configure> bubbles from every child; only the window's own
            # resize is the researcher changing the size of anything.
            return
        if self._resize_save is not None:
            self.root.after_cancel(self._resize_save)
        self._resize_save = self.root.after(RESIZE_SAVE_MS, self.remember_size)

    def _cancel_resize_save(self):
        if self._resize_save is not None:
            try:
                self.root.after_cancel(self._resize_save)
            except Exception:
                pass
            self._resize_save = None

    def interface_size(self):
        """The interface's size in pixels, whichever mode is showing.

        In GUI mode the window *is* the interface. In editor mode the interface
        is the canvas, and the window is that plus the toolbar — so resizing
        either mode describes the same thing, and changing one changes the other.
        """
        # Both readings are of the area the researcher's elements live in, never
        # of the window around it. That is what makes the two modes comparable:
        # the top bar is iterlab's, and is not part of anyone's interface.
        if self.mode == GUI:
            return (
                max(self._content.winfo_width(), 1),
                max(self._content.winfo_height(), 1),
            )
        canvas = getattr(self._built, "canvas", None)
        if canvas is None:  # pragma: no cover - only between teardown and build
            window = self.interface.layout.window
            return window.width, window.height
        return max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)

    def remember_size(self) -> bool:
        """Write the current size into the layout, so reopening restores it.

        Saved from **either** mode now. They describe one number between them,
        which is the whole point: resize the editor and the interface follows,
        resize the interface and the editor follows.
        """
        self._resize_save = None
        if self._switching:
            return False
        try:
            width, height = self.interface_size()
        except Exception:
            # The window is going away. A pending save that fires into a
            # destroyed root is what printed "invalid command name" on close.
            return False
        if width <= 1 or height <= 1:
            # Not yet mapped, or minimised. Neither is a size anyone chose.
            return False
        if not self.interface.layout.resize(width, height):
            return False
        self.interface.save_layout()
        return True

    def chrome_height(self) -> int:
        """How much of the window the top bar takes, in pixels.

        Asked of the bar itself rather than measured as window-minus-content.
        A measurement is only true once Tk has laid the window out, and this is
        needed *while* building one - taking it too early produced a one-pixel
        canvas and a window that then shrank to its floor.
        """
        return self._chrome.winfo_reqheight() + SEPARATOR_HEIGHT

    def toolbar_allowance(self) -> int:
        """How much wider the editor window is than the interface."""
        collapsed = getattr(self.interface.layout, "toolbar_collapsed", False)
        return TOOLBAR_ALLOWANCE if collapsed else SIDEBAR_ALLOWANCE

    def _size_for(self, mode):
        """Window size for a mode, in pixels.

        One number describes both: the interface's own size. GUI mode is exactly
        that; editor mode is that plus the toolbar beside it, so the canvas comes
        out the same pixel size as the window the researcher will run in.

        The editor used to add the toolbar *and* apply a floor of its own, which
        is what made the two modes different shapes - an element drawn square
        came out stretched, because the canvas and the interface were not the
        same rectangle.
        """
        window = self.interface.layout.window
        width = max(window.width, MIN_INTERFACE_WIDTH)
        height = max(window.height, MIN_INTERFACE_HEIGHT) + self.chrome_height()
        if mode != EDITOR:
            return width, height
        # Taller than the interface when the interface is short, so the toolbar
        # always has room for its own controls. The canvas does not grow into
        # that - see Designer, which pins it to the interface's own height.
        return width + self.toolbar_allowance(), max(height, MIN_EDITOR_HEIGHT)

    def apply_size_for_mode(self) -> None:
        """Set the window to the size this mode should be.

        Both modes are derived from one remembered number, so switching is not
        a resize the researcher has to think about: the canvas keeps its pixels
        and the window grows or shrinks by the width of the toolbar.
        """
        self.root.update_idletasks()
        width, height = self._size_for(self.mode)
        if (self.root.winfo_width(), self.root.winfo_height()) == (width, height):
            # Already right. Resizing a window that is the correct size costs
            # nothing visually but can cost the window its focus on X11, and
            # then nothing typed reaches anything.
            return
        self.root.geometry(f"{width}x{height}")
        # Wait for the new size to be real before returning, so whatever is
        # built next is built at that size and not at the old one.
        #
        # `geometry` only asks. Tk applies the change on a later pass, and
        # `update_idletasks` is not that pass - measured, not assumed: with it
        # the plots still rendered at the old width first. Only `update` lands
        # the resize, which costs every plot on screen an extra full render on
        # every mode switch. Three plots went from six renders to nine.
        #
        # `update` runs pending event handlers, so a click on the top bar can
        # arrive in the middle of a rebuild. `busy` is what refuses it.
        self.root.update()

    @property
    def busy(self) -> bool:
        """True while a mode switch is part-built.

        Between teardown and the new mode being constructed there is no
        interface: `self._built` is stale and the widgets it names are gone.
        Resizing the window mid-switch runs the event loop, so a second click
        on the top bar really can arrive in that window - and a rebuild
        starting inside a rebuild tears down what the outer one is holding.
        """
        return self._switching

    def build(self, mode) -> None:
        """Build `mode` into the content frame, replacing whatever was there."""
        self.teardown()
        self._switching = True
        try:
            self.mode = mode
            self.apply_size_for_mode()
            self._built = self._construct(mode)
            # Let Tk apply the geometry before listening again, or the first
            # Configure we hear is the window still at its old width.
            self.root.update_idletasks()
        finally:
            self._switching = False
            self._cancel_resize_save()

    def restart_session(self) -> None:
        """Throw the session away and start again in GUI mode.

        The one way to re-run `on_startup`, now that toggling preserves the
        session instead of discarding it.
        """
        if self.busy:
            return
        self.session.restart()
        self.build(GUI)
        self._mode_toggle.refresh()

    def save_screenshot(self):
        """Write a PNG of the interface beside the interface's own files.

        Returns the path, or None if capture was not possible here. A failure is
        reported like any other fault and never takes the window down: a
        screenshot is a convenience, and a convenience that can kill the session
        is not one (Principle III).
        """
        from . import screenshot as screenshot_mod

        if self.busy:
            return None
        try:
            path = screenshot_mod.save(
                self._content, self.interface.dir, self.interface.name
            )
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            from ..runtime.faults import HANDLER_RAISED, Fault

            sink = getattr(self._built, "sink", None)
            if sink is not None:
                sink.report(Fault.from_exception(exc, HANDLER_RAISED))
            else:  # pragma: no cover - only in editor mode with no sink
                print(f"iterlab: could not save a screenshot: {exc}")
            return None

        self._mode_toggle.announce(f"Saved {path.name}")
        print(f"iterlab: screenshot saved to {path}")
        return path

    def rerun_startup(self) -> bool:
        """Run `on_startup` again over the live session, keeping the data.

        Delegates to GUI mode, which owns the dispatcher. Meaningless in the
        editor, where nothing is running.
        """
        if self.busy:
            return False
        rerun = getattr(self._built, "rerun_startup", None)
        return False if rerun is None else bool(rerun())

    def mark_startup_stale(self, stale) -> None:
        """Let the chrome reflect that `on_startup` has been edited."""
        self._mode_toggle.set_startup_stale(stale)

    def restart_app(self) -> None:
        """Restart cold: everything from disk, as if freshly launched.

        Stronger than `restart_session`, which keeps the layout that is already
        in memory. This re-reads the layout file, forgets the researcher's
        module, and begins a new session — so it also picks up a layout file
        edited by hand, and leaves nothing at all carried over.

        It stays in the mode it was pressed in. Restarting is not a request to
        be moved to a different screen, and a researcher who presses this while
        arranging a layout should still be arranging a layout afterwards.

        The window is deliberately not resized back to the layout's size. That
        size is advisory, and rearranging someone's desktop is not part of what
        they asked for.
        """
        from ..runtime import loader as loader_mod

        if self.busy:
            return
        self.teardown()
        loader_mod.forget(self.interface.code_path)
        self.session.restart()

        # A layout file edited by hand can be invalid, and a restart that died
        # on one would take the window with it - the exact failure Principle III
        # forbids. Keep the layout already in memory, carry on, and say so.
        fault = None
        try:
            self.interface.load_layout()
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            from ..runtime.faults import LOAD_FAILED, Fault

            fault = Fault.from_exception(exc, LOAD_FAILED)

        self.build(self.mode)
        self._mode_toggle.refresh()
        if fault is not None:
            sink = getattr(self._built, "sink", None)
            if sink is not None:
                sink.report(fault)

    def toggle(self) -> str:
        """Switch modes. The whole of FR-015 is this method."""
        if self.busy:
            # A second click arriving inside the first switch. Ignored rather
            # than queued: the researcher asked to be in the other mode, and
            # they are about to be.
            return self.mode
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
        # Closing resizes things on the way out, which can schedule one more
        # save. It must not fire into a window that no longer exists.
        self._cancel_resize_save()
        try:
            self.root.unbind("<Configure>")
        except Exception:
            pass
        for frame in (self._content, self._chrome):
            if frame is not None:
                frame.destroy()
        if self._owns_root:
            self.root.destroy()
