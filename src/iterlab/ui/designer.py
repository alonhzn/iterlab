"""Editor mode: the canvas, the palette, and the properties panel.

Layout changes persist as they are made — the researcher never issues a save
(FR-008). Creating an element appends exactly one stub (FR-009). Nothing here
modifies a line the researcher wrote; the project's one exception is
`codegen.rename`, reached only through `apply_properties`.

Direct manipulation has three modes, decided by where the press lands:

    on a resize handle of the selection  -> resize from that edge or corner
    inside an element                    -> select it and move it
    on empty canvas, dragged              -> rubber-band a new element
    on empty canvas, clicked              -> place one at its default size

All three work in pixel space and convert to normalized fractions once, on
release. Doing the arithmetic in one coordinate system avoids the sign errors
that come from a canvas whose y-axis points down and a layout whose y-axis
points up.
"""

from __future__ import annotations

import tkinter as tk

from ..codegen import inject
from ..codegen import rename as rename_mod
from ..codegen import templates
from ..errors import CodeFileUnparseable, IterlabError
from ..layout.schema import DEFAULT_SIZE, TEXT_TYPES, Element, Rect, validate_tag
from . import theme
from .palette import Palette
from .scroll import ScrollableColumn
from .properties import PropertiesPanel

SIDEBAR_WIDTH = 210
FILL = theme.ELEMENT_FILL
OUTLINE = theme.ELEMENT_EDGE
SELECTED_OUTLINE = theme.ACCENT
HANDLE_FILL = theme.SURFACE

#: Half-extent of a resize handle's grab area, in pixels. Generous on purpose:
#: an 8 px reach means a 16 px target, which is grabbable without precision.
HANDLE_REACH = 8
HANDLE_DRAW = 4

#: An element may not be dragged smaller than this, in pixels. Below it the
#: element becomes impossible to grab again.
MIN_SIZE_PIXELS = 16

#: A press-drag-release shorter than this on empty canvas is a click rather
#: than a drawn rectangle. A click still places an element, at the default size
#: for its type, centred where you clicked.
MIN_DRAG_PIXELS = 12

#: Which pointer to show over each handle.
#:
#: X11 cursor-font names throughout. Tk on Windows also accepts its own
#: `size_nw_se` / `size_ne_sw`, and those were used here first — but X11 does
#: not have them, so on Linux every diagonal handle silently showed no cursor
#: at all. The guard in _set_cursor caught the error; nothing reported it.
#: These names work on all three platforms, and
#: test_every_cursor_name_is_valid_on_this_platform keeps it that way.
CURSORS = {
    "nw": "top_left_corner",
    "ne": "top_right_corner",
    "sw": "bottom_left_corner",
    "se": "bottom_right_corner",
    "n": "sb_v_double_arrow",
    "s": "sb_v_double_arrow",
    "w": "sb_h_double_arrow",
    "e": "sb_h_double_arrow",
}
MOVE_CURSOR = "fleur"
CREATE_CURSOR = "crosshair"


class Designer:
    def __init__(self, app):
        self.app = app
        self.interface = app.interface
        self.layout = app.interface.layout
        self.selected = None
        self._drag = None
        self._rubber_band = None
        self._items = {}
        self._cursor = None

        container = tk.Frame(app.content)
        container.pack(fill="both", expand=True)

        # Scrollable: Tk stops *mapping* children that no longer fit rather
        # than clipping them, so an overflowing sidebar loses widgets silently.
        self.sidebar = ScrollableColumn(container, SIDEBAR_WIDTH)
        self.sidebar.outer.pack(side="left", fill="y")
        self.palette = Palette(self.sidebar.inner, on_select=None)
        self.properties = PropertiesPanel(self.sidebar.inner, self)
        self.sidebar.bind_wheel_to_children()

        tk.Frame(container, bg=theme.BORDER, width=1).pack(side="left", fill="y")

        self.canvas = tk.Canvas(container, bg=theme.SURFACE, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<Escape>", lambda _e: self.select(None))
        self.canvas.bind("<Delete>", lambda _e: self.delete_selected())
        self.canvas.bind("<BackSpace>", lambda _e: self.delete_selected())
        self.canvas.focus_set()

        self.redraw()

    def teardown(self):
        """Nothing to release: the designer holds no session state."""

    # -- geometry --------------------------------------------------------

    def _size(self):
        """Canvas size in pixels.

        Falls back to the requested size: an unmapped canvas reports a width of
        1, which would collapse every coordinate to the same point.
        """
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1:
            width = self.canvas.winfo_reqwidth()
        if height <= 1:
            height = self.canvas.winfo_reqheight()
        return max(width, 1), max(height, 1)

    def _to_pixels(self, rect):
        w, h = self._size()
        x0 = rect.left * w
        x1 = (rect.left + rect.width) * w
        y0 = (1.0 - rect.bottom - rect.height) * h
        y1 = (1.0 - rect.bottom) * h
        return x0, y0, x1, y1

    def _to_fractions(self, x0, y0, x1, y1):
        """Pixel box to a valid Rect.

        Width is clamped against the already-clamped left edge rather than
        independently, because `Rect` rejects left + width > 1 and clamping the
        two separately can produce exactly that.
        """
        w, h = self._size()
        left = max(0.0, min(min(x0, x1) / w, 1.0))
        right = max(0.0, min(max(x0, x1) / w, 1.0))
        top = max(0.0, min(min(y0, y1) / h, 1.0))
        bottom = max(0.0, min(max(y0, y1) / h, 1.0))
        return Rect(
            left=left,
            bottom=max(0.0, 1.0 - bottom),
            width=max(1e-3, min(right - left, 1.0 - left)),
            height=max(1e-3, min(bottom - top, bottom)),
        )

    def _default_rect_at(self, x, y, element_type):
        """A default-sized element centred on a click, nudged to stay in view.

        Sizes are fractions (schema.DEFAULT_SIZE), so they scale with the
        window rather than being pinned to whatever resolution happened to be
        in use when the element was placed.
        """
        w, h = self._size()
        fw, fh = DEFAULT_SIZE[element_type]
        fw, fh = min(fw, 1.0), min(fh, 1.0)
        left = x / w - fw / 2
        bottom = (1.0 - y / h) - fh / 2  # canvas y points down, layout y points up
        return Rect(
            left=max(0.0, min(left, 1.0 - fw)),
            bottom=max(0.0, min(bottom, 1.0 - fh)),
            width=fw,
            height=fh,
        )

    def _clamp_box(self, x0, y0, x1, y1):
        """Order the corners, enforce a minimum size, keep it on the canvas."""
        w, h = self._size()
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        x0 = max(0, min(x0, w - MIN_SIZE_PIXELS))
        y0 = max(0, min(y0, h - MIN_SIZE_PIXELS))
        x1 = min(w, max(x1, x0 + MIN_SIZE_PIXELS))
        y1 = min(h, max(y1, y0 + MIN_SIZE_PIXELS))
        return (x0, y0, x1, y1)

    def _shift_box(self, box, dx, dy):
        """Translate without resizing.

        The size is preserved and the whole box clamped, rather than clamping
        each edge, so dragging into a wall slides the element along it instead
        of squashing it.
        """
        w, h = self._size()
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        x0 = max(0, min(x0 + dx, w - bw))
        y0 = max(0, min(y0 + dy, h - bh))
        return (x0, y0, x0 + bw, y0 + bh)

    def _resize_box(self, box, handle, x, y):
        """Move only the edges named by the handle.

        `"nw"` contains both `"n"` and `"w"`, so corners fall out of the same
        two tests that drive the edges.
        """
        x0, y0, x1, y1 = box
        if "w" in handle:
            x0 = x
        if "e" in handle:
            x1 = x
        if "n" in handle:
            y0 = y
        if "s" in handle:
            y1 = y
        return self._clamp_box(x0, y0, x1, y1)

    def _handle_points(self, x0, y0, x1, y1):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return {
            "nw": (x0, y0), "n": (mx, y0), "ne": (x1, y0),
            "w": (x0, my), "e": (x1, my),
            "sw": (x0, y1), "s": (mx, y1), "se": (x1, y1),
        }

    def _handle_at(self, x, y):
        """Which resize handle is under the pointer, if any.

        Only the selection has handles, so an unselected element cannot be
        resized by accident.
        """
        if not self.selected or self.selected not in self.layout.elements:
            return None
        box = self._to_pixels(self.layout.elements[self.selected].position)
        for name, (hx, hy) in self._handle_points(*box).items():
            if abs(x - hx) <= HANDLE_REACH and abs(y - hy) <= HANDLE_REACH:
                return name
        return None

    # -- drawing ---------------------------------------------------------

    def _live_box(self, name):
        """The box to draw for `name` — the drag preview if one is in flight."""
        if self._drag and self._drag.get("name") == name:
            return self._drag["box"]
        return self._to_pixels(self.layout.elements[name].position)

    def redraw(self):
        self.canvas.delete("all")
        self._items.clear()
        for name, element in self.layout.elements.items():
            x0, y0, x1, y1 = self._live_box(name)
            selected = name == self.selected
            rect_id = self.canvas.create_rectangle(
                x0, y0, x1, y1,
                fill=FILL.get(element.type, "#eeeeee"),
                outline=SELECTED_OUTLINE if selected else OUTLINE.get(element.type, theme.BORDER_STRONG),
                width=2 if selected else 1,
            )
            self.canvas.create_text(
                (x0 + x1) / 2, (y0 + y1) / 2, text=name,
                fill=theme.TEXT, font=theme.FONT_BOLD,
            )
            self._items[rect_id] = name
            if selected:
                self._draw_handles(x0, y0, x1, y1)

    def _draw_handles(self, x0, y0, x1, y1):
        for hx, hy in self._handle_points(x0, y0, x1, y1).values():
            self.canvas.create_rectangle(
                hx - HANDLE_DRAW, hy - HANDLE_DRAW,
                hx + HANDLE_DRAW, hy + HANDLE_DRAW,
                fill=HANDLE_FILL, outline=SELECTED_OUTLINE, width=2,
            )

    # -- pointer feedback ------------------------------------------------

    def _set_cursor(self, name):
        if name == self._cursor:
            return
        try:
            self.canvas.configure(cursor=name)
        except tk.TclError:
            # Not every platform honours every X11 cursor name. A wrong-looking
            # pointer is not worth an exception.
            return
        self._cursor = name

    def _on_hover(self, event):
        """Say what a press would do here, before it happens."""
        if self._drag:
            return
        handle = self._handle_at(event.x, event.y)
        if handle:
            self._set_cursor(CURSORS[handle])
        elif self._element_at(event.x, event.y):
            self._set_cursor(MOVE_CURSOR)
        else:
            self._set_cursor(CREATE_CURSOR)

    # -- selection, move, resize, creation --------------------------------

    def _element_at(self, x, y):
        for item in reversed(self.canvas.find_overlapping(x, y, x, y)):
            if item in self._items:
                return self._items[item]
        return None

    def _on_press(self, event):
        self.canvas.focus_set()

        # A handle takes priority over the element under it: the corner of a
        # selected element is both, and resizing is the more specific intent.
        handle = self._handle_at(event.x, event.y)
        if handle:
            self._drag = {
                "mode": "resize",
                "handle": handle,
                "name": self.selected,
                "box": self._to_pixels(self.layout.elements[self.selected].position),
                "start": self._to_pixels(self.layout.elements[self.selected].position),
                "origin": (event.x, event.y),
            }
            return

        hit = self._element_at(event.x, event.y)
        if hit:
            if hit != self.selected:
                self.select(hit)
            box = self._to_pixels(self.layout.elements[hit].position)
            self._drag = {
                "mode": "move",
                "name": hit,
                "box": box,
                "start": box,
                "origin": (event.x, event.y),
            }
            return

        self.select(None)
        self._drag = {"mode": "create", "origin": (event.x, event.y), "name": None}

    def _on_drag(self, event):
        if not self._drag:
            return
        mode = self._drag["mode"]
        ox, oy = self._drag["origin"]

        if mode == "create":
            if self._rubber_band is not None:
                self.canvas.delete(self._rubber_band)
            self._rubber_band = self.canvas.create_rectangle(
                ox, oy, event.x, event.y, dash=(4, 2), outline=SELECTED_OUTLINE
            )
            return

        if mode == "move":
            self._drag["box"] = self._shift_box(
                self._drag["start"], event.x - ox, event.y - oy
            )
        else:
            self._drag["box"] = self._resize_box(
                self._drag["start"], self._drag["handle"], event.x, event.y
            )
        self.redraw()

    def _on_release(self, event):
        drag, self._drag = self._drag, None
        if not drag:
            return

        if drag["mode"] == "create":
            if self._rubber_band is not None:
                self.canvas.delete(self._rubber_band)
                self._rubber_band = None
            ox, oy = drag["origin"]
            element_type = self.palette.element_type
            too_small = (
                abs(event.x - ox) < MIN_DRAG_PIXELS
                or abs(event.y - oy) < MIN_DRAG_PIXELS
            )
            rect = (
                self._default_rect_at(event.x, event.y, element_type)
                if too_small
                else self._to_fractions(ox, oy, event.x, event.y)
            )
            self.create_element(element_type, rect)
            return

        name = drag["name"]
        if name not in self.layout.elements:
            self.redraw()
            return
        if drag["box"] == drag["start"]:
            # A click that selected something, not a drag. Writing the file for
            # that would churn the layout on every selection.
            self.redraw()
            return

        self.layout.move(name, self._to_fractions(*drag["box"]))
        self.interface.save_layout()
        # Re-select so the properties panel shows the new numbers.
        self.select(name)

    def select(self, tag):
        self.selected = tag
        self.properties.show(self.layout.elements.get(tag) if tag else None)
        self.sidebar.inner.update_idletasks()
        self.sidebar._on_inner_resize()
        self.sidebar.bind_wheel_to_children()
        self.redraw()

    def create_element(self, element_type, rect, tag=None):
        """Draw one element: layout, then stub, then redraw.

        Named automatically and selected with the name field focused, so the
        default can be accepted by doing nothing or replaced by typing.
        """
        suggested = tag or self.layout.next_tag(element_type)
        try:
            validate_tag(suggested, existing=self.layout.elements)
        except IterlabError as exc:
            self.properties._show_message(str(exc))
            return None

        element = Element(
            tag=suggested,
            type=element_type,
            position=rect,
            label=suggested if element_type in TEXT_TYPES else "",
        )
        self.layout.add(element)
        self.interface.save_layout()
        try:
            # Returns False for a type with no default interaction, such as a
            # label; nothing is written and nothing is wrong.
            inject.append_stub(
                self.interface.code_path, element, templates.default_stub(element)
            )
        except CodeFileUnparseable as exc:
            # The element still exists; only the stub could not be added. Say so
            # rather than appending blindly and risking a duplicate definition.
            self.properties._show_message(f"{exc} The element was added anyway.")
        self.select(element.tag)
        # The tag is offered in the properties panel rather than a modal:
        # placing an element should not stop to ask a question (FR-005a).
        self.properties.focus_tag()
        return element

    def delete_selected(self):
        """Remove the element. Its handler stays — we never destroy code."""
        if not self.selected:
            return
        self.layout.remove(self.selected)
        self.interface.save_layout()
        self.select(None)

    # -- property edits --------------------------------------------------

    def apply_properties(self, current_tag, tag=None, position=None, label=None):
        """Apply typed values. A rename rewrites the code file first (R14)."""
        self.layout.elements[current_tag]  # KeyError if it vanished

        if tag and tag != current_tag:
            validate_tag(
                tag, existing=[t for t in self.layout.elements if t != current_tag]
            )
            # Code file first: if it fails, the layout is untouched and the two
            # files stay consistent.
            rename_mod.rename_handlers(self.interface.code_path, current_tag, tag)
            self.layout.retag(current_tag, tag)
            current_tag = tag

        if position is not None:
            self.layout.move(current_tag, position)
        if label is not None and self.layout.elements[current_tag].displays_text:
            self.layout.relabel(current_tag, label)

        self.interface.save_layout()
        self.select(current_tag)
        return current_tag
