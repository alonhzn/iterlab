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
from ..layout.schema import (
    DEFAULT_SIZE,
    TEXT_TYPES,
    Element,
    Rect,
    default_text,
    validate_tag,
)
from . import theme
from .palette import Palette
from .tooltip import PointerTip
from .scroll import ScrollableColumn
from .properties import PropertiesPanel

SIDEBAR_WIDTH = 210

#: Collapsed, the toolbar keeps just enough width to say what it is. A bare
#: arrow would be cheaper in pixels and worse to meet: "Toolbar" tells you what
#: expanding gets you, where a chevron on an empty strip does not.
TOOLBAR_WIDTH = 86

#: The hair line between the toolbar and the canvas. Named because the window
#: allowances in `app` are these widths plus this, and a test holds them in step.
SEPARATOR_WIDTH = 1
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
        self.collapsed = bool(getattr(self.layout, "toolbar_collapsed", False))

        self.sidebar = ScrollableColumn(container, SIDEBAR_WIDTH)
        self.sidebar.outer.pack(side="left", fill="y")
        self._toolbar_header(self.sidebar.inner)
        self.palette = Palette(self.sidebar.inner, on_select=None)
        self.properties = PropertiesPanel(self.sidebar.inner, self)
        # Traced rather than hooked through the palette's own callback, so a
        # type chosen programmatically counts exactly as a clicked card does.
        self.palette.selected.trace_add("write", self._on_palette_change)
        self.sidebar.bind_wheel_to_children()

        # The collapsed face, packed in the sidebar's place when it is folded.
        self.strip = tk.Frame(container, width=TOOLBAR_WIDTH, bg=theme.BG)
        self.strip.pack_propagate(False)
        self._strip_face(self.strip)

        tk.Frame(container, bg=theme.BORDER, width=SEPARATOR_WIDTH).pack(
            side="left", fill="y"
        )

        self.canvas = tk.Canvas(container, bg=theme.SURFACE, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._tag_tip = PointerTip(self.canvas)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", lambda _e: self._tag_tip.hide())
        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<Escape>", lambda _e: self.select(None))
        self.canvas.bind("<Delete>", lambda _e: self.delete_selected())
        self.canvas.bind("<BackSpace>", lambda _e: self.delete_selected())
        self.canvas.focus_set()

        self._apply_collapsed()
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
        for tag, element in self.layout.elements.items():
            x0, y0, x1, y1 = self._live_box(tag)
            selected = tag == self.selected
            # Preview the element's own styling, so choosing a colour can be
            # judged here rather than only after toggling to GUI mode. The
            # type's default tint stands in when nothing has been set.
            style = element.style
            fill = style.background or FILL.get(element.type, "#eeeeee")
            edge = SELECTED_OUTLINE if selected else (
                style.edge or OUTLINE.get(element.type, theme.BORDER_STRONG)
            )
            rect_id = self.canvas.create_rectangle(
                x0, y0, x1, y1,
                fill=fill, outline=edge,
                width=2 if selected else max(style.edge_width, 1),
                stipple="" if style.visible else "gray50",
            )
            self.canvas.create_text(
                (x0 + x1) / 2, (y0 + y1) / 2,
                text=element.label or tag if element.displays_text else tag,
                fill=style.text_color or theme.TEXT,
                font=(style.font or theme.FONT[0],
                      max(7, min(style.font_size or 9, 18)),
                      "bold" if style.bold else "normal"),
            )
            self._items[rect_id] = tag
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
            self._tag_tip.hide()
            return
        handle = self._handle_at(event.x, event.y)
        tag = self._element_at(event.x, event.y)
        if handle:
            self._set_cursor(CURSORS[handle])
        elif tag:
            self._set_cursor(MOVE_CURSOR)
        else:
            self._set_cursor(CREATE_CURSOR)
        self._show_tag_tip(tag, event)

    def _show_tag_tip(self, tag, event):
        """Name the element under the pointer, for the ones that hide their tag.

        An element showing text shows the *text*, so while designing there is no
        way to tell which `ev.<tag>` it is without selecting it and reading the
        properties panel. An axes is left out deliberately: it already has its
        tag drawn on it, so a tooltip would only repeat what is there.
        """
        element = self.layout.elements.get(tag) if tag else None
        if element is None or not element.displays_text:
            self._tag_tip.hide()
            return
        # x_root is absent from a synthesised event; derive it from the canvas
        # so this works whether the motion came from Tk or from a test.
        x_root = getattr(event, "x_root", None)
        y_root = getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            x_root = self.canvas.winfo_rootx() + event.x
            y_root = self.canvas.winfo_rooty() + event.y
        self._tag_tip.show_for(f"tag: {tag}", x_root + 14, y_root + 20)

    # -- selection, move, resize, creation --------------------------------

    def _element_at(self, x, y):
        for item in reversed(self.canvas.find_overlapping(x, y, x, y)):
            if item in self._items:
                return self._items[item]
        return None

    def _on_press(self, event):
        self._tag_tip.hide()
        # Before anything: a value typed into the properties panel and not yet
        # committed would otherwise be lost the moment this rebuilds the panel.
        # focus_set() below cannot do it - Tk delivers the resulting FocusOut on
        # the next pass through the event loop, long after that has happened.
        self.properties.commit_pending()
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

        # Empty canvas. What happens next depends on whether the researcher has
        # armed a type in the palette.
        self.select(None)
        if self.palette.element_type is None:
            # Nothing armed, so this is not an attempt to draw anything. It is
            # the ordinary "click the background to get out of what I was
            # doing": the selection is dropped above, the pending property edit
            # was committed at the top of this method, and focus has moved to
            # the canvas. Starting a create drag here is what used to litter the
            # layout with elements nobody asked for.
            return
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
            # One pick places one element. Leaving the type armed is how a
            # researcher ends up with three buttons stacked on top of each other
            # while trying to click somewhere else.
            self.palette.clear()
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
        # Deliberately does NOT commit pending edits. `select` is the refresh
        # path - it is how a drag, a resize and an apply all put the panel back
        # in step - and committing here writes the panel's now-stale text over
        # the change that just happened, snapping a dragged element home.
        # Committing belongs on the events where focus actually leaves: a press
        # on the canvas, a palette choice, opening the drawer.
        self.selected = tag
        self.properties.show(self.layout.elements.get(tag) if tag else None)
        self.sidebar.inner.update_idletasks()
        self.sidebar._on_inner_resize()
        self.sidebar.bind_wheel_to_children()
        self.redraw()

    # -- the toolbar -----------------------------------------------------

    def _toolbar_header(self, parent):
        """The row that folds the toolbar away."""
        row = tk.Frame(parent, bg=theme.BG, cursor="hand2")
        row.pack(fill="x", padx=10, pady=(10, 0))
        arrow = tk.Canvas(row, width=12, height=12, bg=theme.BG, highlightthickness=0)
        arrow.pack(side="left")
        # Drawn, not a glyph: a chevron character depends on the platform font
        # having it, and renders as a hollow box when it does not.
        arrow.create_polygon(9, 2, 9, 10, 3, 6, fill=theme.TEXT_MUTED, outline="")
        label = tk.Label(
            row, text="Toolbar", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        )
        label.pack(side="left", padx=(5, 0))
        for widget in (row, arrow, label):
            widget.bind("<Button-1>", lambda _e: self.toggle_toolbar())

    def _strip_face(self, parent):
        """What is left when it is folded: the word, and the way back."""
        row = tk.Frame(parent, bg=theme.BG, cursor="hand2")
        row.pack(side="top", fill="x", padx=8, pady=10)
        arrow = tk.Canvas(row, width=12, height=12, bg=theme.BG, highlightthickness=0)
        arrow.pack(side="left")
        arrow.create_polygon(3, 2, 3, 10, 9, 6, fill=theme.TEXT_MUTED, outline="")
        label = tk.Label(
            row, text="Toolbar", bg=theme.BG, fg=theme.TEXT_MUTED,
            font=theme.FONT_SMALL, anchor="w",
        )
        label.pack(side="left", padx=(4, 0))
        for widget in (row, arrow, label):
            widget.bind("<Button-1>", lambda _e: self.toggle_toolbar())

    def _apply_collapsed(self):
        """Show whichever face matches the current state."""
        if self.collapsed:
            self.sidebar.outer.pack_forget()
            self.strip.pack(side="left", fill="y", before=self.canvas)
        else:
            self.strip.pack_forget()
            self.sidebar.outer.pack(side="left", fill="y", before=self.canvas)

    def toggle_toolbar(self) -> bool:
        """Fold the toolbar away, or bring it back.

        The window changes width by the difference, so the canvas keeps exactly
        the pixels it had: folding the toolbar gives you room on the desk, not a
        different interface.
        """
        self.collapsed = not self.collapsed
        self.layout.toolbar_collapsed = self.collapsed
        self._apply_collapsed()
        self.interface.save_layout()
        self.app.apply_size_for_mode()
        self.app.root.update_idletasks()
        self.redraw()
        return self.collapsed

    def _on_palette_change(self, *_args):
        """Choosing a different element type is also "focus went elsewhere"."""
        self.properties.commit_pending()

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
            # A working default rather than the tag: a new button that says
            # "Click here!" is a control, where one saying `cmd_0` is a
            # placeholder the researcher has to fix before showing anyone.
            label=default_text(element_type) if element_type in TEXT_TYPES else "",
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

    def apply_properties(self, current_tag, tag=None, position=None, label=None,
                         style=None, extensions=None):
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
            # Carry the session's figure across, or the plot would blank on the
            # next switch while its data quietly stayed under the old tag.
            self.app.session.retag(current_tag, tag)
            current_tag = tag

        if position is not None:
            self.layout.move(current_tag, position)
        if label is not None and self.layout.elements[current_tag].displays_text:
            self.layout.relabel(current_tag, label)
        if style:
            self.layout.restyle(current_tag, **style)
        if extensions is not None and self.layout.elements[current_tag].filters_files:
            self.layout.set_extensions(current_tag, extensions)

        self.interface.save_layout()
        self.select(current_tag)
        return current_tag
