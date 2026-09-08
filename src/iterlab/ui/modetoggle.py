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
        # to start over. This is the strong one: everything re-read from disk,
        # as if the command had just been run again. Available in both modes,
        # because re-reading a hand-edited layout file is worth having while
        # editing too, and because a control that vanishes is worse than one
        # that is occasionally not needed.
        self.restart = ttk.Button(
            app.chrome, text="Restart app", command=app.restart_app
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

