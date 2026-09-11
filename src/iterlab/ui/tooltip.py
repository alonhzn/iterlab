"""Hover text for chrome controls.

Tk has no tooltip of its own, and the controls in the top bar are the kind where
a wrong guess is expensive — one of them throws the session away. A label is
only so wide; the sentence explaining what a button will actually do belongs
somewhere that costs nothing to read and nothing to ignore.

Deliberately not a dialog and never focus-stealing: it is a borderless toplevel
that appears under the pointer and disappears when it leaves.
"""

from __future__ import annotations

import tkinter as tk

from . import theme

#: Long enough not to flash while the pointer crosses a button on its way
#: somewhere else, short enough to feel like an answer rather than a wait.
DELAY_MS = 450

#: Shorter, for the editor canvas. There the pointer is already on the thing
#: being asked about and the answer is one word, so the chrome delay reads as a
#: hesitation. Not zero: it would flicker on every pass across the canvas.
FAST_DELAY_MS = 200


class Tooltip:
    """Attach hover text to one widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._after_id = None
        self._window = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._cancel, add="+")
        # A click means the researcher has decided; the explanation is now noise.
        widget.bind("<ButtonPress>", self._cancel, add="+")

    # -- timing ----------------------------------------------------------

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(DELAY_MS, self.show)

    def _cancel(self, _event=None):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.hide()

    # -- the window ------------------------------------------------------

    def show(self):
        if self._window is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except tk.TclError:  # pragma: no cover - the widget went away
            return

        window = tk.Toplevel(self.widget)
        # No title bar, no taskbar entry, and never takes focus from the app.
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            window,
            text=self.text,
            bg=theme.TOOLTIP_BG,
            fg=theme.TOOLTIP_TEXT,
            font=theme.FONT_SMALL,
            justify="left",
            wraplength=320,
            padx=8,
            pady=5,
            relief="solid",
            borderwidth=1,
        ).pack()
        self._window = window

    def hide(self):
        if self._window is not None:
            self._window.destroy()
            self._window = None

    @property
    def visible(self) -> bool:
        return self._window is not None


class PointerTip:
    """Hover text for something that is not a widget of its own.

    Canvas items cannot carry `<Enter>` and `<Leave>` the way widgets do, so
    this is driven from a motion handler instead: it is told what the pointer is
    over, and shows or hides itself accordingly.

    It does not follow the pointer while visible. Once it has appeared for a
    target it stays put until the target changes, because a label that chases
    the cursor is harder to read than one that holds still.
    """

    def __init__(self, widget, delay_ms=FAST_DELAY_MS):
        self.widget = widget
        self.delay_ms = delay_ms
        self.text = ""
        self._after_id = None
        self._window = None
        self._at = (0, 0)

    def show_for(self, text, x_root, y_root) -> None:
        """Point at something. Repeated calls for the same text do nothing."""
        if text == self.text and (self._window is not None or self._after_id is not None):
            return
        self._cancel()
        self.text = text
        self._at = (x_root, y_root)
        self._after_id = self.widget.after(self.delay_ms, self._pop)

    def hide(self) -> None:
        self._cancel()
        self.text = ""

    # -- internals -------------------------------------------------------

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._window is not None:
            self._window.destroy()
            self._window = None

    def _pop(self):
        self._after_id = None
        if not self.text:
            return
        x, y = self._at
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{int(x)}+{int(y)}")
        tk.Label(
            window,
            text=self.text,
            bg=theme.TOOLTIP_BG,
            fg=theme.TOOLTIP_TEXT,
            font=theme.FONT_SMALL,
            padx=6,
            pady=3,
            relief="solid",
            borderwidth=1,
        ).pack()
        self._window = window

    @property
    def visible(self) -> bool:
        return self._window is not None
