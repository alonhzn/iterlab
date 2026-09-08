"""The properties panel.

Every property shown is editable, including the name (FR-006b). Anything
settable by dragging is also settable as a typed value, and the two must
produce identical results (FR-006c).

Edits commit on Enter or when the field loses focus. There is no Apply button:
a value you have typed and tabbed away from is a value you meant, and making
the researcher confirm it twice is the kind of ceremony this project exists to
remove.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..errors import IterlabError
from ..layout.schema import Rect
from . import theme

GEOMETRY_FIELDS = ("left", "bottom", "width", "height")
LABELS = {
    "name": "Name",
    "left": "Left",
    "bottom": "Bottom",
    "width": "Width",
    "height": "Height",
    "label": "Label",
}


class PropertiesPanel:
    def __init__(self, parent, designer):
        self.designer = designer
        self.frame = tk.Frame(parent, bg=theme.BG)
        self.frame.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 10))

        tk.Label(
            self.frame, text="PROPERTIES", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self._empty = tk.Label(
            self.frame,
            text="Nothing selected.\n\nClick an element on the canvas to edit it.",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
            justify="left", anchor="w", wraplength=165,
        )
        self._body = tk.Frame(self.frame, bg=theme.BG)
        self._entries = {}

        self._message = tk.Label(
            self.frame, text="", bg=theme.BG, fg=theme.DANGER,
            font=theme.FONT_SMALL, wraplength=165, justify="left", anchor="w",
        )
        self._message.pack(side="bottom", fill="x", pady=(6, 0))

        # Packed now, before the body, and never re-packed. Tk allocates space
        # in packing order, so this cannot be the thing squeezed off the bottom
        # when the panel is taller than the sidebar.
        self._danger_zone = tk.Frame(self.frame, bg=theme.BG)
        self._danger_zone.pack(side="bottom", fill="x", pady=(8, 0))

        self.element_name = None
        #: Guards the commit-on-focus-loss path. Rebuilding the panel destroys
        #: focused entries, and Tk fires <FocusOut> as it does — which would
        #: re-enter apply() with half-destroyed widgets.
        self._busy = False

        self.show(None)

    # -- rendering -------------------------------------------------------

    def show(self, element):
        """Render `element`, or a clear empty state when nothing is selected."""
        previous = self._busy
        self._busy = True
        try:
            self._clear_message()
            for child in self._body.winfo_children():
                child.destroy()
            self._entries.clear()

            if element is None:
                self.element_name = None
                self._body.pack_forget()
                self._clear_delete_control()
                self._empty.pack(side="top", fill="x", pady=6)
                return

            self._empty.pack_forget()
            self._body.pack(side="top", fill="x")
            self.element_name = element.name

            self._readonly_row("Type", element.type)
            self._row("name", element.name)
            self._section("POSITION & SIZE")
            self._geometry_grid(element.position)
            if element.displays_text:
                self._section("TEXT")
                self._row("label", element.label)
            self._fill_delete_control()
        finally:
            self._busy = previous

    def _geometry_grid(self, rect):
        grid = tk.Frame(self._body, bg=theme.BG)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)
        for index, field in enumerate(GEOMETRY_FIELDS):
            row, column = divmod(index, 2)
            tk.Label(
                grid, text=LABELS[field], bg=theme.BG, fg=theme.TEXT_MUTED,
                font=theme.FONT_SMALL, anchor="w",
            ).grid(row=row, column=column * 2, sticky="w", padx=(0, 4), pady=2)
            entry = ttk.Entry(grid, font=theme.FONT, width=6)
            entry.insert(0, f"{getattr(rect, field):g}")
            self._bind_commit(entry)
            entry.grid(row=row, column=column * 2 + 1, sticky="ew", padx=(0, 8), pady=2)
            self._entries[field] = entry

    def _bind_commit(self, entry):
        entry.bind("<Return>", self._commit)
        entry.bind("<KP_Enter>", self._commit)
        entry.bind("<FocusOut>", self._commit)
        entry.bind("<Escape>", lambda _e: self.show(self._current_element()))

    def _section(self, title):
        tk.Label(
            self._body, text=title, bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        ).pack(fill="x", pady=(9, 2))

    def _readonly_row(self, title, value):
        row = tk.Frame(self._body, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=title, width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")
        tk.Label(
            row, text=str(value), anchor="w",
            bg=theme.BG, fg=theme.TEXT, font=theme.FONT,
        ).pack(side="left", fill="x", expand=True)

    def _row(self, key, value):
        row = tk.Frame(self._body, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=LABELS.get(key, key), width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")

        entry = ttk.Entry(row, font=theme.FONT)
        entry.insert(0, str(value))
        self._bind_commit(entry)
        entry.pack(side="left", fill="x", expand=True)
        self._entries[key] = entry

    def _fill_delete_control(self):
        self._clear_delete_control()
        ttk.Separator(self._danger_zone, orient="horizontal").pack(fill="x", pady=(0, 8))
        ttk.Button(
            self._danger_zone, text="Delete element", style="Danger.TButton",
            command=self.designer.delete_selected,
        ).pack(fill="x")
        tk.Label(
            self._danger_zone, text="Its handler stays in your code.",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
            wraplength=165, justify="left", anchor="w",
        ).pack(fill="x", pady=(3, 0))

    def _clear_delete_control(self):
        for child in self._danger_zone.winfo_children():
            child.destroy()

    # -- applying --------------------------------------------------------

    def _current_element(self):
        if self.element_name is None:
            return None
        return self.designer.layout.elements.get(self.element_name)

    def values(self):
        return {k: e.get() for k, e in self._entries.items()}

    def focus_name(self):
        """Put the cursor in the name field with the default selected.

        This is how a newly drawn element offers its name (FR-005a): the
        default is already there, so accepting it needs no typing, and typing
        replaces it. A modal dialog would also satisfy the requirement, but it
        stops the researcher on every single placement - and it stops an
        automated test suite dead.
        """
        entry = self._entries.get("name")
        if entry is None:
            return
        entry.focus_set()
        entry.selection_range(0, "end")
        entry.icursor("end")

    def _unchanged(self, raw, element):
        """True when the fields still show exactly what the element holds.

        Compared as displayed text rather than as numbers, so a value that has
        just been written and re-rendered always compares equal. That is what
        stops commit-on-focus-loss from re-entering itself.
        """
        if raw.get("name", element.name).strip() != element.name:
            return False
        for field in GEOMETRY_FIELDS:
            if raw.get(field, "") != f"{getattr(element.position, field):g}":
                return False
        if element.displays_text and raw.get("label", element.label) != element.label:
            return False
        return True

    def _commit(self, _event=None):
        """Enter, or focus leaving a field. Both mean 'I meant that'."""
        if self._busy:
            return
        self.apply()

    def apply(self):
        """Push typed values back to the layout.

        An invalid value is rejected with an explanation and the element is left
        exactly as it was — the panel never accepts something it will discard
        (FR-006e).
        """
        if self.element_name is None or self._busy:
            return False
        raw = self.values()
        if not raw:
            return False

        element = self._current_element()
        if element is None:
            return False
        if self._unchanged(raw, element):
            self._clear_message()
            return True

        try:
            rect = Rect(*(float(raw[f]) for f in GEOMETRY_FIELDS))
        except (TypeError, ValueError, KeyError) as exc:
            self._show_message(f"Position: {exc}")
            return False

        self._busy = True
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
        finally:
            self._busy = False

        self._clear_message()
        return True

    def _show_message(self, text):
        self._message.configure(text=text)

    def _clear_message(self):
        self._message.configure(text="")
