"""The properties panel.

Every property shown is editable, including the name (FR-006b). Anything
settable by dragging is also settable as a typed value, and the two must produce
identical results — the panel and the canvas are two views of one operation
(FR-006c).
"""

from __future__ import annotations

import tkinter as tk

from ..errors import IterlabError
from ..layout.schema import Rect

GEOMETRY_FIELDS = ("left", "bottom", "width", "height")


class PropertiesPanel:
    def __init__(self, parent, designer):
        self.designer = designer
        self.frame = tk.LabelFrame(parent, text="Properties")
        self.frame.pack(side="top", fill="both", expand=True, padx=6, pady=6)

        self._empty = tk.Label(
            self.frame,
            text="Nothing selected.\nClick an element on the canvas.",
            fg="grey30",
            justify="left",
            wraplength=170,
        )
        self._body = tk.Frame(self.frame)
        self._entries = {}
        self._message = tk.Label(self.frame, text="", fg="firebrick", wraplength=170,
                                 justify="left")
        self._message.pack(side="bottom", fill="x")
        self.element_name = None
        self.show(None)

    # -- rendering -------------------------------------------------------

    def show(self, element):
        """Render `element`, or a clear empty state when nothing is selected."""
        self._clear_message()
        for child in self._body.winfo_children():
            child.destroy()
        self._entries.clear()

        if element is None:
            self.element_name = None
            self._body.pack_forget()
            self._empty.pack(side="top", fill="x", pady=8)
            return

        self._empty.pack_forget()
        self._body.pack(side="top", fill="x")
        self.element_name = element.name

        self._row("type", element.type, editable=False)
        self._row("name", element.name)
        for field in GEOMETRY_FIELDS:
            self._row(field, f"{getattr(element.position, field):g}")
        if element.type == "button":
            self._row("label", element.label)

        tk.Button(self._body, text="Apply", command=self.apply).pack(
            fill="x", pady=(8, 2)
        )

    def _row(self, key, value, editable=True):
        row = tk.Frame(self._body)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=key, width=7, anchor="w").pack(side="left")
        if not editable:
            tk.Label(row, text=str(value), anchor="w", fg="grey30").pack(
                side="left", fill="x", expand=True
            )
            return
        entry = tk.Entry(row)
        entry.insert(0, str(value))
        entry.bind("<Return>", lambda _e: self.apply())
        entry.pack(side="left", fill="x", expand=True)
        self._entries[key] = entry

    # -- applying --------------------------------------------------------

    def values(self):
        return {k: e.get() for k, e in self._entries.items()}

    def apply(self):
        """Push typed values back to the layout.

        An invalid value is rejected with an explanation and the element is left
        exactly as it was — the panel never accepts something it will discard
        (FR-006e).
        """
        if self.element_name is None:
            return False
        raw = self.values()
        try:
            rect = Rect(*(float(raw[f]) for f in GEOMETRY_FIELDS))
        except (TypeError, ValueError) as exc:
            self._show_message(f"Position: {exc}")
            return False

        try:
            self.designer.apply_properties(
                self.element_name,
                name=raw.get("name", self.element_name).strip(),
                position=rect,
                label=raw.get("label"),
            )
        except IterlabError as exc:
            self._show_message(str(exc))
            return False

        self._clear_message()
        return True

    def _show_message(self, text):
        self._message.configure(text=text)

    def _clear_message(self):
        self._message.configure(text="")
