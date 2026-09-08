"""The element-type palette.

Editor mode must show every type that can be added, so the vocabulary is
discoverable without documentation (FR-003a). Presented as icon cards rather
than radio buttons: the icon says what the thing *is* faster than its name
does, which matters for a researcher who has never seen the tool.

`selected` stays a `StringVar` holding the element type, so anything driving
the palette does not need to know it is drawn as cards.
"""

from __future__ import annotations

import tkinter as tk

from ..layout.schema import ELEMENT_TYPES
from . import theme

DISPLAY_NAME = {"axes": "Axes", "button": "Button", "label": "Label"}

#: Deliberately compact: one line per type, icon and name only. The vocabulary
#: is going to grow, and a card tall enough for a description does not survive
#: a dozen element types in a sidebar.
ROW_PAD = 4
ICON_SIZE = 18


class _Card:
    """One clickable type in the palette."""

    def __init__(self, parent, element_type, on_click):
        self.element_type = element_type
        self.selected = False

        self.frame = tk.Frame(
            parent, bg=theme.BG, highlightthickness=1,
            highlightbackground=theme.BORDER, highlightcolor=theme.BORDER,
            cursor="hand2",
        )
        self.frame.pack(fill="x", pady=1)

        inner = tk.Frame(self.frame, bg=theme.BG)
        inner.pack(fill="x", padx=7, pady=ROW_PAD)

        self.icon = theme.element_icon(inner, element_type, size=ICON_SIZE)
        self.icon.pack(side="left")

        self.title = tk.Label(
            inner, text=DISPLAY_NAME.get(element_type, element_type),
            bg=theme.BG, fg=theme.TEXT, font=theme.FONT, anchor="w",
        )
        self.title.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # Every child swallows clicks aimed at the row, so bind them all.
        for widget in (self.frame, inner, self.icon, self.title):
            widget.bind("<Button-1>", lambda _e: on_click(element_type))

    def set_selected(self, selected):
        self.selected = selected
        background = theme.ACCENT_SOFT if selected else theme.BG
        edge = theme.ACCENT if selected else theme.BORDER
        icon_colour = theme.ACCENT if selected else theme.TEXT

        self.frame.configure(highlightbackground=edge, highlightcolor=edge, bg=background)
        for widget in self.frame.winfo_children():
            self._paint(widget, background)
        self.title.configure(fg=theme.ACCENT if selected else theme.TEXT)

        # The icon is drawn, so recolouring means redrawing it.
        self.icon.configure(bg=background)
        self.icon.delete("all")
        painter = theme.ICONS.get(self.element_type)
        if painter is not None:
            painter(self.icon, ICON_SIZE, icon_colour)

    def _paint(self, widget, background):
        try:
            widget.configure(bg=background)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._paint(child, background)


class Palette:
    def __init__(self, parent, on_select=None):
        self.frame = tk.Frame(parent, bg=theme.BG)
        self.frame.pack(side="top", fill="x", padx=10, pady=(12, 4))

        tk.Label(
            self.frame, text="ADD ELEMENT", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.selected = tk.StringVar(value=ELEMENT_TYPES[0])
        self._on_select = on_select
        self._cards = {}

        for element_type in ELEMENT_TYPES:
            self._cards[element_type] = _Card(self.frame, element_type, self._choose)

        tk.Label(
            self.frame,
            text="Drag on the canvas, or click to drop one.",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
            wraplength=165, justify="left", anchor="w",
        ).pack(fill="x", pady=(6, 0))

        # Keep the cards in step with the variable however it is set, so that
        # `palette.selected.set(...)` behaves the same as clicking a card.
        self.selected.trace_add("write", lambda *_: self._refresh())
        self._refresh()

    def _choose(self, element_type):
        self.selected.set(element_type)
        if self._on_select:
            self._on_select(element_type)

    def _refresh(self):
        current = self.selected.get()
        for element_type, card in self._cards.items():
            card.set_selected(element_type == current)

    @property
    def element_type(self) -> str:
        return self.selected.get()
