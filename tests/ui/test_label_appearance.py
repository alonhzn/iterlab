"""A label looks like text, not like a card.

On the editor canvas it is drawn in the canvas's own colour with a black edge:
its previous tint was near-identical to the file selector's, so a glance could
not tell them apart. In the running interface it takes the background behind it
and has no edge, because a caption sitting in a white box is exactly what a
caption should not look like.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.ui import theme

pytestmark = pytest.mark.ui


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
    d.create_element("label", Rect(0.10, 0.60, 0.35, 0.12), tag="status")
    d.create_element("file_select", Rect(0.10, 0.20, 0.35, 0.12), tag="pick")
    d.select(None)
    d.redraw()
    return d


def _rect_for(designer, tag):
    for item, owner in designer._items.items():
        if owner == tag:
            return item
    raise AssertionError(f"no canvas rectangle for {tag}")


# -- on the editor canvas --------------------------------------------------


def test_a_label_is_drawn_in_the_canvas_colour(designer):
    item = _rect_for(designer, "status")
    assert designer.canvas.itemcget(item, "fill") == designer.canvas.cget("bg")


def test_a_label_has_a_black_edge(designer):
    item = _rect_for(designer, "status")
    assert designer.canvas.itemcget(item, "outline") == "#000000"


def test_a_label_no_longer_matches_the_file_selector(designer):
    """The reported problem: two near-identical greens."""
    label = designer.canvas.itemcget(_rect_for(designer, "status"), "fill")
    selector = designer.canvas.itemcget(_rect_for(designer, "pick"), "fill")
    assert label != selector


def test_it_is_still_selectable_despite_looking_transparent(designer):
    """The trap this avoids.

    `fill=""` would be truly transparent, and an unfilled canvas rectangle is
    only hit on its outline - so the label would have stopped being selectable
    or movable anywhere but on its border. Painting it the canvas's own colour
    looks the same and stays clickable.
    """
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements["status"].position)
    centre = (int((x0 + x1) / 2), int((y0 + y1) / 2))
    designer._on_press(_Event(*centre))
    designer._on_release(_Event(*centre))
    assert designer.selected == "status"


def test_it_is_still_movable(designer):
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements["status"].position)
    centre = (int((x0 + x1) / 2), int((y0 + y1) / 2))
    before = designer.layout.elements["status"].position.left
    designer._on_press(_Event(*centre))
    designer._on_drag(_Event(centre[0] + 60, centre[1]))
    designer._on_release(_Event(centre[0] + 60, centre[1]))
    assert designer.layout.elements["status"].position.left != before


def test_the_other_types_keep_their_own_colours(designer):
    """Only the label changed; the tints still tell the rest apart."""
    for kind in ("axes", "button", "text_box", "number_box", "folder_select"):
        assert theme.ELEMENT_FILL[kind] != theme.SURFACE, kind


# -- in the running interface ----------------------------------------------


@pytest.fixture
def gui(designer):
    app = designer.app
    app.toggle()
    return app


def test_a_label_takes_the_background_behind_it(gui):
    widget = gui.built.handles["status"].widget
    assert widget.cget("bg") == widget.master.cget("bg")


def test_a_label_has_no_edge(gui):
    widget = gui.built.handles["status"].widget
    assert int(widget.cget("highlightthickness")) == 0


def test_a_button_is_left_alone(gui):
    """Only the label's default changed."""
    gui.toggle()
    gui.built.create_element("button", Rect(0.6, 0.6, 0.2, 0.1), tag="go")
    gui.toggle()
    widget = gui.built.handles["go"].widget
    assert widget.cget("bg") != widget.master.cget("bg")


def test_a_chosen_background_still_wins(gui):
    """This is a default, not a rule - researcher code overrides it."""
    gui.built.ev.status.background = "#fff3cd"
    assert gui.built.handles["status"].widget.cget("bg") == "#fff3cd"


def test_a_chosen_edge_still_wins(gui):
    gui.built.ev.status.edge_width = 2
    assert int(gui.built.handles["status"].widget.cget("highlightthickness")) == 2


def test_the_transparent_default_survives_a_mode_switch(gui):
    gui.toggle()
    gui.toggle()
    widget = gui.built.handles["status"].widget
    assert widget.cget("bg") == widget.master.cget("bg")
