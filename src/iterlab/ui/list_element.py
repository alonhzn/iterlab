"""A list: rows of text that research code fills, and a person selects from.

    ev.lst_0.append("run 12: ok")          # add a row at the bottom
    ev.lst_0.insert(0, "header")            # add one anywhere
    del ev.lst_0[3]                         # remove one; the rows below move up
    ev.lst_0[2] = "new text"                # replace a row's text
    ev.lst_0.length                         # how many rows (also len(ev.lst_0))
    ev.lst_0.style_line(2, text_color="red", bold=True)
    ev.lst_0.selected                       # index, or None; a tuple if multi

A row's style belongs to the row, not to its position. Deleting row 1 moves
the red row from index 3 to index 2, and it is still red. The same goes for
which rows are selected. That is why every row carries an id that never
changes, and its Tk tag is named after the id rather than the index.

Built on a read-only Tk `Text`, one line per row. `Listbox` was the obvious
choice and cannot do it: it colours rows but gives every row the same font, so
per-row bold, italic and size would be impossible. A `Text` line takes any font
and simply grows taller for a bigger one.

The rows are the session's, not the layout's (Principle II): the layout says how
a list looks and behaves, and code fills it. They survive a trip to the editor
like any other runtime state, and a hard reset or a relaunch empties them.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace
from tkinter import ttk
import tkinter as tk

from ..runtime.dispatch import Event
from . import theme
from .elements import BASE_FONT_SIZE, STYLE_PROPERTY_NAMES, ElementHandle

#: Every style property `ev.lst_0` exposes for the list as a whole.
LIST_STYLE_PROPERTIES = STYLE_PROPERTY_NAMES + ("highlight",)

#: What `style_line` can set on one row. The rest - an edge, alignment, being
#: enabled - only make sense for the list as a whole.
LINE_STYLE_KEYS = ("text_color", "highlight", "font", "font_size", "bold", "italic")

SELECTED_BG = theme.ACCENT
SELECTED_FG = "#ffffff"

#: Breathing room above and below each row's text, in pixels.
ROW_SPACING = 2

_row_ids = itertools.count()


@dataclass
class _Row:
    text: str
    style: dict = field(default_factory=dict)
    id: int = field(default_factory=lambda: next(_row_ids))

    @property
    def tag(self) -> str:
        return f"row{self.id}"


def _font_tuple(style):
    """A Tk font description. A tuple rather than a `Font` object, which Tk
    forgets the moment Python collects it - taking a row's font with it."""
    description = [style.font or theme.FONT[0], style.font_size or BASE_FONT_SIZE]
    if style.bold:
        description.append("bold")
    if style.italic:
        description.append("italic")
    return tuple(description)


class ListHandle(ElementHandle):
    """What `ev.lst_0` is. Behaves like a Python list of strings, mostly."""

    STYLE_PROPERTIES = LIST_STYLE_PROPERTIES

    # Declared for editors; reached through __getattr__/__setattr__, exactly as
    # on the text-bearing handles.
    background: str | None
    text_color: str | None
    edge: str | None
    edge_width: int
    font: str | None
    font_size: int | None
    bold: bool
    italic: bool
    align: str
    enabled: bool
    visible: bool
    highlight: str | None

    def __init__(self, element, frame, text):
        super().__init__(element, frame)
        self.__dict__["_text"] = text
        self.__dict__["_rows"] = []
        #: Selected rows, by id: they follow their rows as indexes shift.
        self.__dict__["_picked"] = []

    def __getattr__(self, name):
        if name in LIST_STYLE_PROPERTIES:
            return getattr(self.__dict__["_style"], name)
        raise AttributeError(name)

    def __bool__(self):
        # An empty list is still an element. `if ev.lst_0:` reading as "is
        # there anything in it" would be one surprise; iterlab's own checks for
        # a handle finding an empty one falsy would be a worse one. `.length`
        # says how many rows there are.
        return True

    # -- reading ---------------------------------------------------------

    @property
    def length(self) -> int:
        """How many rows the list has."""
        return len(self._rows)

    def __len__(self):
        return len(self._rows)

    @property
    def lines(self) -> tuple:
        """Every row's text, top to bottom. A copy: changing it changes nothing."""
        return tuple(row.text for row in self._rows)

    def __iter__(self):
        return iter(self.lines)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return list(self.lines[index])
        return self._rows[self._index(index)].text

    # -- changing the rows -------------------------------------------------

    def append(self, text) -> None:
        """Add a row at the bottom."""
        self.insert(len(self._rows), text)

    def extend(self, texts) -> None:
        """Add several rows at the bottom, faster than appending one at a time."""
        follow = self._at_bottom()
        with self._editing():
            for text in texts:
                self._insert_row(len(self._rows), _Row(str(text)))
        if follow:
            self._text.see("end")

    def insert(self, index, text) -> None:
        """Add a row so that it becomes row `index`. Rows from there move down."""
        position = self._index(index, allow_end=True)
        follow = position == len(self._rows) and self._at_bottom()
        with self._editing():
            self._insert_row(position, _Row(str(text)))
        if follow:
            self._text.see("end")

    def __setitem__(self, index, text) -> None:
        """Replace a row's text. Its style and whether it is selected stay."""
        row = self._rows[self._index(index)]
        row.text = str(text)
        line = self._line(row)
        with self._editing():
            self._text.delete(f"{line}.0", f"{line}.end")
            self._text.insert(f"{line}.0", row.text, self._tags_for(row))

    def __delitem__(self, index) -> None:
        if isinstance(index, slice):
            for position in sorted(range(*index.indices(len(self._rows))), reverse=True):
                self._delete_row(position)
            return
        self._delete_row(self._index(index))

    def delete(self, index) -> None:
        """Remove a row. The rows below it move up to close the gap."""
        del self[index]

    def clear(self) -> None:
        """Remove every row."""
        with self._editing():
            self._text.delete("1.0", "end")
        for row in self._rows:
            self._text.tag_delete(row.tag)
        self._rows.clear()
        self._picked.clear()

    # -- one row's look ----------------------------------------------------

    def style_line(self, index, **changes) -> None:
        """Set how one row looks, over the list's own style.

        Any of text_color, highlight, font, font_size, bold and italic. `None`
        puts a property back to the list's own. The style stays with the row
        when rows above it are added or deleted.
        """
        unknown = set(changes) - set(LINE_STYLE_KEYS)
        if unknown:
            raise TypeError(
                f"style_line() takes {', '.join(LINE_STYLE_KEYS)}, "
                f"not {', '.join(sorted(unknown))}"
            )
        row = self._rows[self._index(index)]
        merged = dict(row.style)
        merged.update(changes)
        merged = {k: v for k, v in merged.items() if v is not None}
        # Checked through Style, so a bad colour or size is refused here with
        # the same message the editor gives, before anything changes.
        replace(self.style, **merged)
        row.style = merged
        self._configure_row(row)

    # -- selection ---------------------------------------------------------

    @property
    def selected(self):
        """The selected row: an index, or None.

        With multi-select turned on in the editor, a tuple of indexes in order,
        empty when nothing is selected.
        """
        positions = sorted(self._position(row_id) for row_id in self._picked)
        if self.element.multi_select:
            return tuple(positions)
        return positions[0] if positions else None

    @selected.setter
    def selected(self, value):
        if value is None:
            wanted = []
        elif isinstance(value, int):
            wanted = [value]
        else:
            wanted = list(value)
            if not self.element.multi_select and len(wanted) > 1:
                raise ValueError(
                    f"{self.tag} selects one row at a time; turn on Multi-select "
                    f"in the editor to select several"
                )
        rows = [self._rows[self._index(i)] for i in wanted]
        self._pick([row.id for row in rows])
        if rows:
            self._text.see(f"{self._line(rows[0])}.0")

    # -- internals ---------------------------------------------------------

    def _index(self, index, allow_end=False) -> int:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError(f"row indexes are whole numbers, not {type(index).__name__}")
        count = len(self._rows)
        position = index + count if index < 0 else index
        limit = count if allow_end else count - 1
        if not 0 <= position <= limit:
            raise IndexError(f"{self.tag} has no row {index} - it has {count}")
        return position

    def _position(self, row_id) -> int:
        for position, row in enumerate(self._rows):
            if row.id == row_id:
                return position
        raise KeyError(row_id)  # pragma: no cover - picked rows are always present

    def _line(self, row) -> int:
        return self._rows.index(row) + 1

    def _editing(self):
        text = self._text

        class _Open:
            def __enter__(self_inner):
                text.configure(state="normal")

            def __exit__(self_inner, *exc):
                text.configure(state="disabled")
                return False

        return _Open()

    def _tags_for(self, row):
        tags = ["line", row.tag]
        if row.id in self._picked:
            tags.append("picked")
        return tuple(tags)

    def _insert_row(self, position, row) -> None:
        self._rows.insert(position, row)
        self._text.insert(f"{position + 1}.0", row.text + "\n", self._tags_for(row))
        if row.style:
            self._configure_row(row)

    def _delete_row(self, position) -> None:
        row = self._rows[position]
        with self._editing():
            self._text.delete(f"{position + 1}.0", f"{position + 2}.0")
        self._text.tag_delete(row.tag)
        del self._rows[position]
        if row.id in self._picked:
            self._picked.remove(row.id)

    def _configure_row(self, row) -> None:
        if not row.style:
            self._text.tag_configure(row.tag, font="", foreground="", background="")
            return
        merged = replace(self.style, **row.style)
        self._text.tag_configure(
            row.tag,
            font=_font_tuple(merged) if set(row.style) & {"font", "font_size", "bold", "italic"} else "",
            foreground=row.style.get("text_color", ""),
            background=row.style.get("highlight", ""),
        )
        # A tag created after "picked" would draw over the selection colour.
        self._text.tag_raise("picked")

    def _pick(self, row_ids) -> None:
        self.__dict__["_picked"] = list(dict.fromkeys(row_ids))
        self._text.tag_remove("picked", "1.0", "end")
        for row in self._rows:
            if row.id in self._picked:
                line = self._line(row)
                self._text.tag_add("picked", f"{line}.0", f"{line + 1}.0")

    def _at_bottom(self) -> bool:
        return not self._rows or self._text.yview()[1] >= 0.999

    def _row_at(self, x, y):
        """The row under a point in the widget, or None over empty space."""
        if not self._rows:
            return None
        line = int(self._text.index(f"@{x},{y}").split(".")[0])
        if line > len(self._rows):
            return None
        box = self._text.dlineinfo(f"{line}.0")
        if box is None or y > box[1] + box[3]:
            return None
        return line - 1

    def _apply(self):
        style = self.__dict__["_style"]
        text = self._text
        text.configure(
            bg=style.background or theme.SURFACE,
            fg=style.text_color or theme.TEXT if style.enabled else theme.TEXT_MUTED,
            font=_font_tuple(style),
            highlightthickness=style.edge_width,
            highlightbackground=style.edge or theme.BORDER_STRONG,
            highlightcolor=style.edge or theme.BORDER_STRONG,
            selectbackground=style.background or theme.SURFACE,
            inactiveselectbackground=style.background or theme.SURFACE,
            selectforeground=style.text_color or theme.TEXT,
        )
        text.tag_configure(
            "line",
            justify=style.align,
            background=style.highlight or "",
            spacing1=ROW_SPACING,
            spacing3=ROW_SPACING,
        )
        text.tag_configure(
            "picked",
            background=SELECTED_BG if style.enabled else theme.BORDER_STRONG,
            foreground=SELECTED_FG,
        )
        # A row's own font is the list's with the row's changes on top, so a
        # change to the list's font has to reach every row that has one.
        for row in self._rows:
            if row.style:
                self._configure_row(row)
        text.tag_raise("picked")
        self._apply_visibility()

    # -- surviving a rebuild -----------------------------------------------

    def _presentation(self) -> dict:
        state = super()._presentation()
        state["rows"] = [(row.text, dict(row.style)) for row in self._rows]
        state["picked"] = [self._position(row_id) for row_id in self._picked]
        return state

    def _restore(self, state) -> None:
        super()._restore(state)
        if "rows" not in state:
            return
        self.clear()
        with self._editing():
            for text, style in state["rows"]:
                self._insert_row(len(self._rows), _Row(text, dict(style)))
        picked = [self._rows[i].id for i in state.get("picked", ()) if i < len(self._rows)]
        if not self.element.multi_select:
            picked = picked[:1]
        self._pick(picked)


def build_list(parent, element, dispatcher):
    frame = tk.Frame(parent, bg=theme.SURFACE)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    text = tk.Text(
        frame, wrap="none", cursor="arrow", undo=False, takefocus=1,
        insertwidth=0, padx=4, pady=2, relief="flat", borderwidth=0,
        exportselection=False, state="disabled",
    )
    text.grid(row=0, column=0, sticky="nsew")

    vertical = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)

    def autohide(bar, row, column):
        # Shown only when there is something to scroll to, so a list that fits
        # does not spend its width on a scrollbar.
        def on_scroll(first, last):
            bar.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                bar.grid_remove()
            else:
                bar.grid(row=row, column=column, sticky="ns" if column else "ew")
        return on_scroll

    text.configure(yscrollcommand=autohide(vertical, 0, 1))
    if element.scroll_x:
        text.configure(xscrollcommand=autohide(horizontal, 1, 0))

    handle = ListHandle(element, frame, text)
    tag = element.tag

    def fire(kind, index=None, **fields):
        row_text = handle._rows[index].text if index is not None else None
        dispatcher.invoke(
            f"on_{kind}_{tag}",
            Event(kind=kind, tag=tag, index=index, text=row_text, **fields),
        )

    def click(event, mode):
        text.focus_set()
        if not handle.style.enabled:
            return "break"
        index = handle._row_at(event.x, event.y)
        if index is None:
            return "break"
        row_id = handle._rows[index].id
        picked = list(handle._picked)
        if not element.multi_select or mode == "only":
            picked = [row_id]
        elif mode == "add":
            picked.append(row_id)
        elif mode == "remove":
            picked = [p for p in picked if p != row_id]
        handle._pick(picked)
        fire("clicked", index, button="left")
        return "break"

    def other_button(event, name):
        if handle.style.enabled:
            index = handle._row_at(event.x, event.y)
            if index is not None:
                fire("clicked", index, button=name)
        return "break"

    def double(event):
        if handle.style.enabled:
            index = handle._row_at(event.x, event.y)
            if index is not None:
                fire("clicked", index, button="left", double=True)
        return "break"

    def step(event, delta):
        """Up and Down move the selection, and count as clicking that row."""
        if not handle.style.enabled or not handle._rows:
            return "break"
        current = [handle._position(p) for p in handle._picked]
        if current:
            index = max(0, min(len(handle._rows) - 1, (min(current) if delta < 0 else max(current)) + delta))
        else:
            index = 0 if delta > 0 else len(handle._rows) - 1
        handle._pick([handle._rows[index].id])
        text.see(f"{index + 1}.0")
        fire("key", index, key=event.keysym)
        fire("clicked", index, key=event.keysym)
        return "break"

    def key(event):
        selected = [handle._position(p) for p in handle._picked]
        fire("key", min(selected) if selected else None, key=event.keysym)
        return "break"

    def sideways(event, units):
        if element.scroll_x:
            text.xview_scroll(units, "units")
        return "break"

    def pointer(kind):
        def handler(event):
            fire(kind, handle._row_at(event.x, event.y))
        return handler

    aqua = text.tk.call("tk", "windowingsystem") == "aqua"
    add, remove = ("Command", "Option") if aqua else ("Control", "Alt")

    text.bind("<Button-1>", lambda e: click(e, "only"))
    text.bind(f"<{add}-Button-1>", lambda e: click(e, "add"))
    text.bind(f"<{remove}-Button-1>", lambda e: click(e, "remove"))
    text.bind("<Double-Button-1>", double)
    for sequence in ("<B1-Motion>", "<Triple-Button-1>", "<Shift-Button-1>",
                     f"<{add}-a>", f"<{add}-slash>"):
        text.bind(sequence, lambda _e: "break")
    text.bind("<ButtonRelease-2>", lambda e: other_button(e, "middle"))
    text.bind("<ButtonRelease-3>", lambda e: other_button(e, "right"))
    text.bind("<Up>", lambda e: step(e, -1))
    text.bind("<Down>", lambda e: step(e, 1))
    text.bind("<Left>", lambda e: sideways(e, -2))
    text.bind("<Right>", lambda e: sideways(e, 2))
    text.bind("<KeyPress>", key)
    if not element.scroll_x:
        for sequence in ("<Shift-MouseWheel>", "<Shift-Button-4>", "<Shift-Button-5>"):
            text.bind(sequence, lambda _e: "break")
    text.bind("<Enter>", pointer("hover"))
    text.bind("<Motion>", pointer("motion"))

    handle._apply()
    return handle
