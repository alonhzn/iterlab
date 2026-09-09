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

from dataclasses import replace

from ..errors import IterlabError
from ..layout.schema import ALIGNMENTS, Rect, basic_properties, style_fields_for
from . import theme

GEOMETRY_FIELDS = ("left", "bottom", "width", "height")
STYLE_LABELS = {
    "background": "Fill",
    "text_color": "Text",
    "edge": "Border",
    "edge_width": "Width",
    "font": "Font",
    "font_size": "Size",
    "bold": "Bold",
    "italic": "Italic",
    "align": "Align",
    "enabled": "Enabled",
    "visible": "Visible",
}

COLOUR_FIELDS = ("background", "text_color", "edge")

LABELS = {
    "tag": "Tag",
    "left": "Left",
    "bottom": "Bottom",
    "width": "Width",
    "height": "Height",
    "label": "Label",
    "extensions": "Types",
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
        #: Where row helpers put their widgets. Swapped to the drawer while the
        #: advanced sections are built, so one set of helpers serves both.
        self._target = self._body
        #: Whether the drawer is open. Kept on the panel rather than rebuilt per
        #: element: a researcher who opened it to nudge a colour should not have
        #: it slam shut the moment they select something else.
        self.advanced_open = False
        self._advanced = None
        self._drawer_arrow = None
        self._drawer_label = None
        self._entries = {}
        self._swatches = {}

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

        self.element_tag = None
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
            self._swatches.clear()

            if element is None:
                self.element_tag = None
                self._body.pack_forget()
                self._clear_delete_control()
                self._empty.pack(side="top", fill="x", pady=6)
                return

            self._empty.pack_forget()
            self._body.pack(side="top", fill="x")
            self.element_tag = element.tag

            # Basic: what you had to decide to have made the element at all.
            self._readonly_row("Type", element.type)
            self._row("tag", element.tag)
            for prop in basic_properties(element.type):
                if prop == "label":
                    self._row("label", element.label)
                elif prop == "extensions":
                    self._row("extensions", element.extensions)
                    self._hint("Comma separated, e.g. txt, csv. Blank shows every file.")

            # Everything else lives behind the drawer. It is *built* either way,
            # so the values are always there to commit and nothing depends on
            # whether the researcher happened to open it - only packed or not.
            self._build_drawer()
            self._target = self._advanced
            try:
                self._section("POSITION & SIZE")
                self._geometry_grid(element.position)
                self._style_section(element)
            finally:
                self._target = self._body

            self._fill_delete_control()
        finally:
            self._busy = previous

    def _build_drawer(self):
        """The "More" header and the frame it reveals."""
        header = tk.Frame(self._body, bg=theme.BG, cursor="hand2")
        header.pack(fill="x", pady=(10, 0))

        # Drawn rather than a glyph character: an arrow depends on the platform
        # font having it, and a missing glyph renders as a hollow box.
        self._drawer_arrow = tk.Canvas(
            header, width=12, height=12, bg=theme.BG, highlightthickness=0
        )
        self._drawer_arrow.pack(side="left", padx=(0, 5))
        self._drawer_label = tk.Label(
            header, text="", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        )
        self._drawer_label.pack(side="left")

        for widget in (header, self._drawer_arrow, self._drawer_label):
            widget.bind("<Button-1>", lambda _e: self.toggle_advanced())

        self._advanced = tk.Frame(self._body, bg=theme.BG)
        self._render_drawer()

    def _render_drawer(self):
        canvas = self._drawer_arrow
        if canvas is None:
            return
        canvas.delete("all")
        # Down when closed (press to open), up when open (press to close).
        points = (
            (2, 4, 10, 4, 6, 10) if not self.advanced_open else (2, 9, 10, 9, 6, 3)
        )
        canvas.create_polygon(*points, fill=theme.TEXT_MUTED, outline="")
        self._drawer_label.configure(text="Less" if self.advanced_open else "More")
        if self.advanced_open:
            self._advanced.pack(fill="x")
        else:
            self._advanced.pack_forget()

    def toggle_advanced(self):
        self.advanced_open = not self.advanced_open
        self._render_drawer()
        return self.advanced_open

    def _geometry_grid(self, rect):
        grid = tk.Frame(self._target, bg=theme.BG)
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

    def _style_section(self, element):
        """Editors for whatever style properties this element type has.

        An axes element only gets `visible`; matplotlib owns the rest of how it
        looks, and offering a fill colour that does nothing would be a lie.
        """
        available = style_fields_for(element.type)
        style = element.style

        if any(f in available for f in COLOUR_FIELDS):
            self._section("COLOUR")
            for field in COLOUR_FIELDS:
                if field in available:
                    self._colour_row(field, getattr(style, field))
            if "edge_width" in available:
                self._style_entry("edge_width", style.edge_width)

        if "font" in available:
            self._section("FONT")
            self._font_row(style.font)
            self._style_entry("font_size", style.font_size)
            self._toggle_row(("bold", style.bold), ("italic", style.italic))
            self._align_row(style.align)

        self._section("STATE")
        toggles = [("visible", style.visible)]
        if "enabled" in available:
            toggles.append(("enabled", style.enabled))
        self._toggle_row(*toggles)

    def _colour_row(self, field, value):
        """A hex entry with a swatch that opens the colour picker."""
        row = tk.Frame(self._target, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=STYLE_LABELS[field], width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")

        entry = ttk.Entry(row, font=theme.FONT)
        entry.insert(0, value or "")
        self._bind_commit(entry)
        entry.pack(side="left", fill="x", expand=True)
        self._entries[field] = entry

        swatch = tk.Frame(
            row, width=20, height=20, bg=value or theme.SURFACE,
            relief="solid", borderwidth=1, cursor="hand2",
        )
        swatch.pack_propagate(False)
        swatch.pack(side="left", padx=(5, 0))
        swatch.bind("<Button-1>", lambda _e, f=field: self._pick_colour(f))
        self._swatches[field] = swatch

    def _pick_colour(self, field):
        """Open the system colour picker and write the result into the entry."""
        from tkinter import colorchooser

        current = self._entries[field].get() or None
        chosen = colorchooser.askcolor(color=current, parent=self.frame)[1]
        if not chosen:
            return
        entry = self._entries[field]
        entry.delete(0, "end")
        entry.insert(0, chosen)
        self.apply()

    def _font_row(self, value):
        row = tk.Frame(self._target, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=STYLE_LABELS["font"], width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")
        box = ttk.Combobox(
            row, values=theme.available_fonts(self.frame), state="readonly",
            font=theme.FONT,
        )
        box.set(value or "(default)")
        box.bind("<<ComboboxSelected>>", self._commit)
        box.pack(side="left", fill="x", expand=True)
        self._entries["font"] = box

    def _style_entry(self, field, value):
        row = tk.Frame(self._target, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=STYLE_LABELS[field], width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")
        entry = ttk.Entry(row, font=theme.FONT, width=6)
        entry.insert(0, "" if value is None else str(value))
        self._bind_commit(entry)
        entry.pack(side="left")
        self._entries[field] = entry

    def _toggle_row(self, *fields):
        row = tk.Frame(self._target, bg=theme.BG)
        row.pack(fill="x", pady=2)
        for field, value in fields:
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(
                row, text=STYLE_LABELS[field], variable=var,
                bg=theme.BG, fg=theme.TEXT, font=theme.FONT_SMALL,
                activebackground=theme.BG, selectcolor=theme.SURFACE,
                highlightthickness=0, anchor="w", command=self._commit,
            ).pack(side="left", padx=(0, 10))
            self._entries[field] = var

    def _align_row(self, value):
        row = tk.Frame(self._target, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Label(
            row, text=STYLE_LABELS["align"], width=7, anchor="w",
            bg=theme.BG, fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
        ).pack(side="left")
        var = tk.StringVar(value=value)
        for option in ALIGNMENTS:
            tk.Radiobutton(
                row, text=option[0].upper(), value=option, variable=var,
                bg=theme.BG, fg=theme.TEXT, font=theme.FONT_SMALL,
                activebackground=theme.BG, selectcolor=theme.SURFACE,
                highlightthickness=0, indicatoron=False, width=2,
                command=self._commit,
            ).pack(side="left", padx=1)
        self._entries["align"] = var

    def _hint(self, text):
        """A line under a field, for a format that is not obvious from its name."""
        tk.Label(
            self._target, text=text, bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w", justify="left", wraplength=165,
        ).pack(fill="x", pady=(0, 4))

    def _section(self, title):
        tk.Label(
            self._target, text=title, bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        ).pack(fill="x", pady=(9, 2))

    def _readonly_row(self, title, value):
        row = tk.Frame(self._target, bg=theme.BG)
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
        row = tk.Frame(self._target, bg=theme.BG)
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
        if self.element_tag is None:
            return None
        return self.designer.layout.elements.get(self.element_tag)

    def values(self):
        """Current editor values. Entries, comboboxes and Vars all read alike."""
        return {key: widget.get() for key, widget in self._entries.items()}

    def _style_changes(self, element):
        """Typed style values, parsed. Raises ValueError on a bad one."""
        available = set(style_fields_for(element.type))
        raw = self.values()
        changes = {}

        for field in COLOUR_FIELDS:
            if field in available and field in raw:
                text = str(raw[field]).strip()
                changes[field] = text or None

        if "edge_width" in available and "edge_width" in raw:
            text = str(raw["edge_width"]).strip()
            changes["edge_width"] = int(text) if text else 0

        if "font" in available and "font" in raw:
            chosen = str(raw["font"])
            changes["font"] = None if chosen in ("", "(default)") else chosen

        if "font_size" in available and "font_size" in raw:
            text = str(raw["font_size"]).strip()
            changes["font_size"] = int(text) if text else None

        for field in ("bold", "italic", "enabled", "visible"):
            if field in available and field in raw:
                changes[field] = bool(raw[field])

        if "align" in available and "align" in raw:
            changes["align"] = str(raw["align"])

        # Build the replacement here so its validation runs *before* anything is
        # applied. Otherwise a bad colour would raise only after the position
        # had already been written, leaving the element half-updated.
        replace(element.style, **changes)
        return changes

    def focus_tag(self):
        """Put the cursor in the tag field with the default selected.

        This is how a newly drawn element offers its tag (FR-005a): the
        default is already there, so accepting it needs no typing, and typing
        replaces it. A modal dialog would also satisfy the requirement, but it
        stops the researcher on every single placement - and it stops an
        automated test suite dead.
        """
        entry = self._entries.get("tag")
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
        if str(raw.get("tag", element.tag)).strip() != element.tag:
            return False
        for field in GEOMETRY_FIELDS:
            if raw.get(field, "") != f"{getattr(element.position, field):g}":
                return False
        if element.displays_text and raw.get("label", element.label) != element.label:
            return False
        if element.filters_files:
            if str(raw.get("extensions", element.extensions)).strip() != element.extensions:
                return False
        try:
            changes = self._style_changes(element)
        except (TypeError, ValueError):
            return False  # invalid input is a change, so apply() can report it
        return all(getattr(element.style, k) == v for k, v in changes.items())

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
        if self.element_tag is None or self._busy:
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

        try:
            style_changes = self._style_changes(element)
        except (TypeError, ValueError) as exc:
            self._show_message(f"Style: {exc}")
            return False

        self._busy = True
        try:
            self.designer.apply_properties(
                self.element_tag,
                tag=str(raw.get("tag", self.element_tag)).strip(),
                position=rect,
                label=raw.get("label"),
                style=style_changes,
                extensions=raw.get("extensions"),
            )
        except (IterlabError, ValueError) as exc:
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
