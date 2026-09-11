"""Adding an element is a deliberate two-step act: pick a type, then place it.

The palette starts with nothing armed and returns to that after each placement,
so one pick places one element. Before this, a type was always armed and any
click on the background produced an element the researcher then had to find and
delete - including the click they meant as "get out of what I was doing".

With nothing armed, clicking the background does what clicking a background
normally does: drops the selection and takes focus away from whatever had it.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

EMPTY = (330, 90)


class _Event:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@pytest.fixture
def designer(make_app):
    app = make_app()
    d = app.built
    d.canvas.configure(width=400, height=400)
    d._size = lambda: (400, 400)
    app.root.update_idletasks()
    return d


def _click(designer, point=EMPTY):
    designer._on_press(_Event(*point))
    designer._on_release(_Event(*point))


def _drag(designer, start, end):
    designer._on_press(_Event(*start))
    designer._on_drag(_Event(*end))
    designer._on_release(_Event(*end))


# -- nothing is armed to begin with ----------------------------------------


def test_the_palette_starts_with_nothing_armed(designer):
    assert designer.palette.element_type is None


def test_no_card_is_highlighted_to_begin_with(designer):
    assert not any(card.selected for card in designer.palette._cards.values())


def test_clicking_the_canvas_creates_nothing(designer):
    _click(designer)
    assert designer.layout.tags() == []


def test_dragging_the_canvas_creates_nothing(designer):
    _drag(designer, (60, 60), (200, 200))
    assert designer.layout.tags() == []


def test_the_hint_says_what_to_do_first(designer):
    assert "Pick a type" in designer.palette.hint.cget("text")


# -- arming, then placing --------------------------------------------------


def test_arming_highlights_the_card(designer):
    designer.palette.selected.set("button")
    assert designer.palette._cards["button"].selected is True


def test_an_armed_type_is_placed_by_a_click(designer):
    designer.palette.selected.set("button")
    _click(designer)
    assert designer.layout.tags() == ["cmd_0"]


def test_an_armed_type_is_placed_by_a_drag(designer):
    designer.palette.selected.set("label")
    _drag(designer, (60, 60), (200, 200))
    assert designer.layout.tags() == ["lbl_0"]


def test_placing_disarms_the_palette(designer):
    """One pick, one element."""
    designer.palette.selected.set("button")
    _click(designer)
    assert designer.palette.element_type is None


def test_placing_removes_the_highlight(designer):
    designer.palette.selected.set("button")
    _click(designer)
    assert not any(card.selected for card in designer.palette._cards.values())


def test_a_second_element_needs_a_second_pick(designer):
    """The point of disarming: a stray click no longer stacks another button."""
    designer.palette.selected.set("button")
    _click(designer)
    _click(designer, (200, 300))
    assert designer.layout.tags() == ["cmd_0"], "the second click placed something"

    designer.palette.selected.set("button")
    _click(designer, (200, 300))
    assert sorted(designer.layout.tags()) == ["cmd_0", "cmd_1"]


# -- what a background click does instead ----------------------------------


def test_clicking_the_background_deselects(designer):
    designer.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    designer.select("go")
    assert designer.selected == "go"

    _click(designer)
    assert designer.selected is None


def test_clicking_the_background_commits_a_pending_edit(designer):
    """Focus leaves the property field, and leaving it is what saves it."""
    designer.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    designer.select("go")
    entry = designer.properties._entries["label"]
    entry.delete(0, "end")
    entry.insert(0, "Run fit")

    _click(designer)
    assert designer.layout.elements["go"].label == "Run fit"


@pytest.fixture
def mapped_designer(mapped, make_app):
    """Tk ignores focus_set on a withdrawn window, so this one needs a real one."""
    app = make_app()
    d = app.built
    d.canvas.configure(width=400, height=400)
    d._size = lambda: (400, 400)
    app.root.update_idletasks()
    return d


def test_clicking_the_background_takes_the_focus(mapped_designer):
    designer = mapped_designer
    designer.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    designer.select("go")
    designer.properties._entries["tag"].focus_set()
    designer.app.root.update()

    _click(designer)
    designer.app.root.update()
    # "focus -lastfor" asks Tk which widget takes focus when this toplevel has
    # it, rather than asking the window manager whether it has focus right now.
    focused = designer.app.root.tk.call("focus", "-lastfor", designer.canvas._w)
    assert str(focused) == str(designer.canvas)


def test_an_existing_element_is_still_selectable_with_nothing_armed(designer):
    """Disarming must not make the canvas inert."""
    designer.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    designer.select(None)
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements["go"].position)
    _click(designer, (int((x0 + x1) / 2), int((y0 + y1) / 2)))
    assert designer.selected == "go"


def test_an_existing_element_is_still_movable_with_nothing_armed(designer):
    designer.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    designer.select("go")
    before = designer.layout.elements["go"].position.left
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements["go"].position)
    centre = (int((x0 + x1) / 2), int((y0 + y1) / 2))
    _drag(designer, centre, (centre[0] + 60, centre[1]))
    assert designer.layout.elements["go"].position.left != before


def test_deleting_still_works_with_nothing_armed(designer):
    designer.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    designer.select("go")
    designer.delete_selected()
    assert designer.layout.tags() == []
