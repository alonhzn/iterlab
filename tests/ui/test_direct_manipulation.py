"""Moving and resizing elements by mouse in editor mode.

Drives the canvas handlers with positioned events, which is what a real drag
delivers. The canvas is given an explicit size so pixel arithmetic is
meaningful — an unmapped widget reports a width of 1.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CANVAS_W, CANVAS_H = 400, 400


class _Event:
    """A press/motion/release event at a point, as Tk delivers it."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


@pytest.fixture
def designer(make_app):
    app = make_app()
    d = app.built
    # Pin the canvas size. These tests are about the drag arithmetic, not about
    # how Tk happens to allocate space, and letting the real allocation vary
    # makes every pixel expectation depend on unrelated layout changes.
    d.canvas.configure(width=CANVAS_W, height=CANVAS_H)
    d._size = lambda: (CANVAS_W, CANVAS_H)
    app.root.update_idletasks()
    # left .25, bottom .25, w .25, h .25  ->  pixels x 100..200, y 200..300
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    return d


def _drag(designer, start, end):
    designer._on_press(_Event(*start))
    designer._on_drag(_Event(*end))
    designer._on_release(_Event(*end))


def _box(designer, name="go"):
    return tuple(round(v) for v in designer._to_pixels(designer.layout.elements[name].position))


def test_the_fixture_lands_where_the_arithmetic_expects(designer):
    assert _box(designer) == (100, 200, 200, 300)


# -- bindings ---------------------------------------------------------------


def test_the_canvas_actually_binds_the_drag_sequences(designer):
    """Wiring, not just mechanism.

    A handler that exists but is bound to nothing is the shape of bug this
    project has already hit twice.
    """
    bound = set(designer.canvas.bind())
    # Tk stores <ButtonPress-1> under its normalized name, <Button-1>.
    for sequence in ("<Button-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Motion>"):
        assert sequence in bound, f"{sequence} is not bound"


# -- moving -----------------------------------------------------------------


def test_dragging_inside_an_element_moves_it(designer):
    _drag(designer, (150, 250), (200, 300))
    assert _box(designer) == (150, 250, 250, 350)


def test_moving_preserves_size(designer):
    before = _box(designer)
    _drag(designer, (150, 250), (110, 210))
    after = _box(designer)
    assert (after[2] - after[0], after[3] - after[1]) == (
        before[2] - before[0],
        before[3] - before[1],
    )


def test_dragging_an_unselected_element_selects_and_moves_it(designer):
    designer.create_element("button", Rect(0.6, 0.6, 0.2, 0.2), tag="other")
    designer.select(None)
    _drag(designer, (280, 100), (300, 120))
    assert designer.selected == "other"
    assert designer.layout.elements["other"].position.left > 0.6


def test_a_move_is_persisted(designer):
    _drag(designer, (150, 250), (180, 280))
    from iterlab.layout import store

    saved = store.load(designer.interface.layout_path)
    assert saved.elements["go"].position.left == pytest.approx(0.325, abs=1e-3)


def test_moving_cannot_push_an_element_off_the_canvas(designer):
    """Dragging into a wall slides along it rather than squashing the element."""
    _drag(designer, (150, 250), (-500, -500))
    x0, y0, x1, y1 = _box(designer)
    assert (x0, y0) == (0, 0)
    assert (x1 - x0, y1 - y0) == (100, 100), "size preserved while clamped"


def test_a_click_without_movement_does_not_rewrite_the_layout(designer):
    before = designer.interface.layout_path.read_bytes()
    designer._on_press(_Event(150, 250))
    designer._on_release(_Event(150, 250))
    assert designer.interface.layout_path.read_bytes() == before


# -- resizing ---------------------------------------------------------------


def test_handles_are_drawn_only_for_the_selection(designer):
    designer.create_element("button", Rect(0.6, 0.6, 0.2, 0.2), tag="other")
    designer.select("go")
    assert designer._handle_at(100, 200) == "nw", "the selection has handles"
    designer.select("other")
    assert designer._handle_at(100, 200) is None, "an unselected element has none"


@pytest.mark.parametrize(
    "handle, point, expected",
    [
        ("e", (260, 250), (100, 200, 260, 300)),   # right edge: width only
        ("w", (60, 250), (60, 200, 200, 300)),     # left edge: width only
        ("s", (150, 360), (100, 200, 200, 360)),   # bottom edge: height only
        ("n", (150, 160), (100, 160, 200, 300)),   # top edge: height only
    ],
)
def test_edge_handles_resize_one_dimension(designer, handle, point, expected):
    origin = designer._handle_points(*designer._to_pixels(
        designer.layout.elements["go"].position
    ))[handle]
    _drag(designer, (round(origin[0]), round(origin[1])), point)
    assert _box(designer) == expected


@pytest.mark.parametrize(
    "handle, point, expected",
    [
        ("se", (260, 360), (100, 200, 260, 360)),
        ("nw", (60, 160), (60, 160, 200, 300)),
        ("ne", (260, 160), (100, 160, 260, 300)),
        ("sw", (60, 360), (60, 200, 200, 360)),
    ],
)
def test_corner_handles_resize_both_dimensions(designer, handle, point, expected):
    origin = designer._handle_points(*designer._to_pixels(
        designer.layout.elements["go"].position
    ))[handle]
    _drag(designer, (round(origin[0]), round(origin[1])), point)
    assert _box(designer) == expected


def test_a_handle_takes_priority_over_moving(designer):
    """A corner is both 'on the element' and 'on a handle'. Resize wins."""
    designer._on_press(_Event(100, 200))  # the nw corner
    assert designer._drag["mode"] == "resize"
    assert designer._drag["handle"] == "nw"
    designer._on_release(_Event(100, 200))


def test_resize_cannot_collapse_an_element(designer):
    """Below a minimum it would become impossible to grab again."""
    _drag(designer, (200, 300), (100, 200))  # drag se corner onto nw
    x0, y0, x1, y1 = _box(designer)
    assert x1 - x0 >= 16
    assert y1 - y0 >= 16


def test_resize_is_persisted(designer):
    _drag(designer, (200, 300), (300, 380))
    from iterlab.layout import store

    saved = store.load(designer.interface.layout_path)
    assert saved.elements["go"].position.width == pytest.approx(0.5, abs=1e-2)


def test_dragging_past_the_edge_clamps_to_the_canvas(designer):
    _drag(designer, (200, 300), (900, 900))
    x0, y0, x1, y1 = _box(designer)
    assert x1 <= CANVAS_W and y1 <= CANVAS_H


# -- the researcher's code is untouched throughout --------------------------


def test_moving_and_resizing_never_touch_the_code_file(designer):
    """Principle V. Layout is layout; code is code."""
    before = designer.interface.code_path.read_bytes()

    _drag(designer, (150, 250), (180, 280))
    assert _box(designer) == (130, 230, 230, 330), "moved"

    # Grab the moved element's own se handle, not empty canvas - a drag that
    # starts on the background is a create, and would legitimately add a stub.
    _drag(designer, (230, 330), (280, 380))
    assert _box(designer) == (130, 230, 280, 380), "resized"

    assert designer.interface.code_path.read_bytes() == before


# -- pointer feedback -------------------------------------------------------


def test_every_cursor_name_is_valid_on_this_platform(designer):
    """Tk rejects an unknown cursor name, and _set_cursor swallows that.

    Windows accepts `size_nw_se`; X11 does not, so on Linux every diagonal
    resize handle silently showed no cursor at all and nothing said so. CI
    found it. This asserts the names are real wherever the suite runs.
    """
    import tkinter

    from iterlab.ui.designer import CREATE_CURSOR, CURSORS, MOVE_CURSOR

    rejected = []
    for name in set(CURSORS.values()) | {MOVE_CURSOR, CREATE_CURSOR}:
        try:
            designer.canvas.configure(cursor=name)
        except tkinter.TclError:
            rejected.append(name)
    assert not rejected, f"not valid cursor names on this platform: {rejected}"


def test_hovering_reports_what_a_press_would_do(designer):
    from iterlab.ui.designer import CREATE_CURSOR, CURSORS, MOVE_CURSOR

    designer._on_hover(_Event(100, 200))
    assert designer._cursor == CURSORS["nw"], "over a corner handle"
    designer._on_hover(_Event(150, 250))
    assert designer._cursor == MOVE_CURSOR, "inside the element"
    designer._on_hover(_Event(370, 60))
    assert designer._cursor == CREATE_CURSOR, "empty canvas"


def test_each_corner_gets_its_own_cursor(designer):
    """Corner-shaped cursors, one per corner.

    The Windows-only `size_nw_se` shared a cursor across a diagonal; the X11
    corner names do not, so each corner points at itself. More informative, and
    it works on every platform.
    """
    from iterlab.ui.designer import CURSORS

    corners = {CURSORS[c] for c in ("nw", "ne", "sw", "se")}
    assert len(corners) == 4, f"corners should be distinguishable, got {corners}"


def test_opposite_edges_share_an_axis_cursor(designer):
    from iterlab.ui.designer import CURSORS

    assert CURSORS["n"] == CURSORS["s"]
    assert CURSORS["w"] == CURSORS["e"]
    assert CURSORS["n"] != CURSORS["w"]


def test_hover_does_not_fight_an_in_flight_drag(designer):
    designer._on_press(_Event(150, 250))
    designer._on_drag(_Event(170, 270))
    cursor = designer._cursor
    designer._on_hover(_Event(370, 60))
    assert designer._cursor == cursor
    designer._on_release(_Event(170, 270))


# -- creation still works ---------------------------------------------------


def test_dragging_empty_canvas_still_creates(designer):
    designer.palette.selected.set("button")
    designer.select(None)
    _drag(designer, (250, 40), (390, 160))
    assert "button_0" in designer.layout.tags()


def test_creating_needs_no_dialog_and_focuses_the_name_field(designer):
    """Placing an element must never stop to ask a question.

    A modal here would satisfy FR-005a but would also make the test suite
    unrunnable without a human, which disqualifies it as a release gate.
    """
    designer.palette.selected.set("button")
    designer.select(None)
    _drag(designer, (300, 100), (300, 100))

    entry = designer.properties._entries["tag"]
    assert entry.get() == "button_0", "the default is pre-filled"
    assert entry.selection_present(), "and selected, so typing replaces it"

    # Tk ignores focus_set on a withdrawn window entirely, so the root has to be
    # mapped for the question to mean anything.
    root = designer.app.root
    root.deiconify()
    try:
        root.update()
        designer.properties.focus_tag()
        root.update_idletasks()
        # "focus -lastfor" asks Tk which widget takes focus when this toplevel
        # has it. `focus_get` asks the window manager whether the toplevel has
        # focus *right now*, and a desktop is free to say no to a test window -
        # which is why that form passed alone and failed in a full suite, where
        # other tests map and unmap this same shared root.
        focused = root.tk.call("focus", "-lastfor", entry._w)
        assert str(focused) == str(entry), "the cursor is already in the name field"
    finally:
        root.withdraw()


def test_a_tiny_drag_counts_as_a_click(designer):
    """A wobble while clicking should not produce a sliver of an element."""
    from iterlab.layout.schema import DEFAULT_SIZE

    designer.palette.selected.set("button")
    designer.select(None)
    _drag(designer, (300, 60), (303, 63))
    placed = designer.layout.elements["button_0"].position
    assert (placed.width, placed.height) == pytest.approx(DEFAULT_SIZE["button"])


# -- click to place at a default size ---------------------------------------


def test_clicking_empty_canvas_places_a_default_sized_element(designer):
    from iterlab.layout.schema import DEFAULT_SIZE

    designer.palette.selected.set("button")
    designer.select(None)
    _drag(designer, (300, 100), (300, 100))  # a click: press and release, no movement

    assert designer.layout.tags() == ["go", "button_0"]
    placed = designer.layout.elements["button_0"].position
    assert (placed.width, placed.height) == pytest.approx(DEFAULT_SIZE["button"])


def test_a_clicked_element_is_centred_on_the_click(designer):
    designer.palette.selected.set("button")
    designer.select(None)
    # Clearly off the "go" fixture element, which occupies x 100-200, y 200-300.
    _drag(designer, (300, 120), (300, 120))

    placed = designer.layout.elements["button_0"].position
    centre_x = placed.left + placed.width / 2
    centre_y = placed.bottom + placed.height / 2
    assert centre_x == pytest.approx(300 / CANVAS_W, abs=1e-3)
    assert centre_y == pytest.approx(1.0 - 120 / CANVAS_H, abs=1e-3)


def test_the_palette_decides_what_a_click_places(designer):
    from iterlab.layout.schema import DEFAULT_SIZE

    designer.palette.selected.set("plot_area")
    designer.select(None)
    _drag(designer, (250, 150), (250, 150))

    placed = designer.layout.elements["plot_0"]
    assert placed.type == "plot_area"
    assert (placed.position.width, placed.position.height) == pytest.approx(
        DEFAULT_SIZE["plot_area"]
    )


def test_a_click_near_the_edge_stays_fully_on_the_canvas(designer):
    designer.palette.selected.set("plot_area")
    designer.select(None)
    _drag(designer, (5, 395), (5, 395))  # bottom-left corner

    placed = designer.layout.elements["plot_0"].position
    assert placed.left >= 0.0
    assert placed.bottom >= 0.0
    assert placed.left + placed.width <= 1.0 + 1e-9
    assert placed.bottom + placed.height <= 1.0 + 1e-9


def test_a_real_drag_still_wins_over_the_default_size(designer):
    designer.palette.selected.set("button")
    designer.select(None)
    _drag(designer, (250, 60), (390, 180))

    placed = designer.layout.elements["button_0"].position
    assert placed.width == pytest.approx(140 / CANVAS_W, abs=1e-2)
    assert placed.height == pytest.approx(120 / CANVAS_H, abs=1e-2)


def test_escape_deselects_now_that_clicking_creates(designer):
    """Clicking empty canvas places an element, so deselecting needs a key."""
    assert designer.selected == "go"
    # Tk stores <Escape> under its normalized name, <Key-Escape>.
    assert "<Key-Escape>" in set(designer.canvas.bind())
    designer.select(None)
    assert designer.selected is None
