"""The element-type palette.

Editor mode must show every type that can be added, so the vocabulary is
discoverable without documentation (FR-003a).
"""

from __future__ import annotations

import tkinter as tk

from ..layout.schema import ELEMENT_TYPES

DISPLAY_NAME = {"plot_area": "Plot area", "button": "Button"}


class Palette:
    def __init__(self, parent, on_select):
        self.frame = tk.LabelFrame(parent, text="Add")
        self.frame.pack(side="top", fill="x", padx=6, pady=6)
        self.selected = tk.StringVar(value=ELEMENT_TYPES[0])
        self._on_select = on_select

        for element_type in ELEMENT_TYPES:
            tk.Radiobutton(
                self.frame,
                text=DISPLAY_NAME.get(element_type, element_type),
                value=element_type,
                variable=self.selected,
                anchor="w",
                command=self._changed,
            ).pack(fill="x")

        tk.Label(
            self.frame,
            text="Drag on the canvas to place one.",
            wraplength=170,
            justify="left",
            fg="grey30",
        ).pack(fill="x", pady=(4, 2))

    def _changed(self):
        if self._on_select:
            self._on_select(self.selected.get())

    @property
    def element_type(self) -> str:
        return self.selected.get()
