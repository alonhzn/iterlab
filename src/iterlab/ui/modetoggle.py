"""The mode toggle: top-left corner, above everything, in both modes.

Chrome, not layout. It never appears in the layout file, cannot be moved or
deleted, and is not reachable from the researcher's code (FR-015c).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme
from .app import EDITOR, GUI

#: Plain words rather than glyphs. An arrow or pencil character depends on the
#: platform font having it, and a missing glyph draws as a hollow box.
LABEL = {EDITOR: "Run it", GUI: "Edit layout"}
CAPTION = {
    EDITOR: "Editing the layout",
    GUI: "Running your code",
}


class ModeToggle:
    """A single control that swaps which mode is built."""

    def __init__(self, app):
        self.app = app

        self.button = ttk.Button(
            app.chrome, text=LABEL[app.mode], style="Accent.TButton",
            command=self._on_click,
        )
        self.button.pack(side="left", anchor="w", padx=10, pady=8)

        # Toggling preserves the session, so there has to be one explicit way
        # to start over - it is how a change to on_startup takes effect.
        self.restart = ttk.Button(
            app.chrome, text="Restart session", command=app.restart_session
        )
        self.restart.pack(side="left", padx=(2, 0))

        self.caption = tk.Label(
            app.chrome, text="", bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL
        )
        self.caption.pack(side="left", padx=8)

        self.refresh()

    def _on_click(self):
        # App.toggle() calls self.refresh() itself once the new mode is built,
        # so the label is never updated before the switch has actually happened.
        self.app.toggle()

    def refresh(self):
        mode = self.app.mode
        self.button.configure(text=LABEL[mode])
        self.caption.configure(text=CAPTION[mode])
        # Restarting is meaningless in the editor: there is no live session to
        # throw away, and the next visit to GUI mode carries one anyway.
        self.restart.state(["!disabled"] if mode == GUI else ["disabled"])

