"""The mode toggle: top-left corner, above everything, in both modes.

Chrome, not layout. It never appears in the layout file, cannot be moved or
deleted, and is not reachable from the researcher's code (FR-015c).
"""

from __future__ import annotations

import tkinter as tk

from .app import EDITOR, GUI

LABEL = {EDITOR: "▶  Use it", GUI: "✎  Edit it"}
TOOLTIP = {
    EDITOR: "Switch to GUI mode and run this interface",
    GUI: "Switch to editor mode and change the layout",
}


class ModeToggle:
    """A single control that swaps which mode is built."""

    def __init__(self, app):
        self.app = app
        self.button = tk.Button(
            app.chrome,
            text=LABEL[app.mode],
            command=self._on_click,
            padx=10,
        )
        # Top-left, and packed into chrome rather than content so it survives
        # every rebuild and can never be obscured by a drawn element (FR-015b).
        self.button.pack(side="left", anchor="nw", padx=4, pady=4)
        self._status = tk.Label(app.chrome, text="", anchor="w")
        self._status.pack(side="left", padx=8)
        self.refresh()

    def _on_click(self):
        # App.toggle() calls self.refresh() itself once the new mode is built,
        # so the label is never updated before the switch has actually happened.
        self.app.toggle()

    def refresh(self):
        self.button.configure(text=LABEL[self.app.mode])
        self._status.configure(
            text="editor mode" if self.app.mode == EDITOR else "GUI mode"
        )
