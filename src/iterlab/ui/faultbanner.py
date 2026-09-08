"""The in-window fault signal.

The second of the two channels FR-033 requires. Full detail goes to stderr; this
exists so a researcher looking at their plots still learns that something broke,
which a terminal message alone cannot guarantee.

Non-blocking by construction: it is a strip in the window, never a dialog. The
researcher keeps using every other element while it shows (FR-033a), and it
clears when corrected code runs (FR-033b) so the window never accumulates stale
warnings.
"""

from __future__ import annotations

import tkinter as tk

BACKGROUND = "#fdecea"
FOREGROUND = "#8a1c11"


class FaultBanner:
    """A `FaultSink` that renders into a Tk frame."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BACKGROUND)
        self.label = tk.Label(
            self.frame,
            text="",
            bg=BACKGROUND,
            fg=FOREGROUND,
            anchor="w",
            justify="left",
            wraplength=900,
        )
        self.label.pack(side="left", fill="x", expand=True, padx=8, pady=4)
        tk.Label(
            self.frame,
            text="full traceback in the terminal",
            bg=BACKGROUND,
            fg=FOREGROUND,
            font=("TkDefaultFont", 8),
        ).pack(side="right", padx=8)
        self.visible = False
        self.current = None

    # -- FaultSink -------------------------------------------------------

    def report(self, fault) -> None:
        where = f"{fault.element}: " if fault.element else ""
        self.label.configure(text=f"⚠  {where}{fault.message}")
        self.current = fault
        self._show()

    def clear(self, element=None) -> None:
        if not self.visible:
            return
        if element is not None and self.current is not None:
            if self.current.element not in (None, element):
                return
        self.current = None
        self._hide()

    # -- rendering -------------------------------------------------------

    def _show(self):
        if not self.visible:
            # Packed at the bottom so it never displaces the researcher's
            # elements, which are placed by fraction of the frame.
            self.frame.pack(side="bottom", fill="x")
            self.visible = True

    def _hide(self):
        if self.visible:
            self.frame.pack_forget()
            self.visible = False

    @property
    def text(self) -> str:
        return self.label.cget("text")
