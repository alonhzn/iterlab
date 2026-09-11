"""Hovering an element in the editor names its tag.

An element that shows text shows the *text*, so while designing there is no way
to tell which `ev.<tag>` a button reading "Click here!" actually is without
selecting it and reading the properties panel. The tooltip answers that where
the question is asked.

Editor only. In the running interface the tags are the researcher's own code and
a tooltip over every control would be noise.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.ui.tooltip import DELAY_MS, FAST_DELAY_MS

pytestmark = pytest.mark.ui


class _Motion:
    """A motion event as Tk delivers one, with the root coordinates."""

    def __init__(self, x, y, x_root=None, y_root=None):
        self.x = x
        self.y = y
        if x_root is not None:
            self.x_root = x_root
        if y_root is not None:
            self.y_root = y_root


@pytest.fixture
def designer(make_app):
    app = make_app()
    d = app.built
    d.canvas.configure(width=400, height=400)
    d._size = lambda: (400, 400)
    app.root.update_idletasks()
    d.create_element("button", Rect(0.10, 0.60, 0.30, 0.20), tag="run_fit")
    d.create_element("axes", Rect(0.10, 0.10, 0.30, 0.20), tag="spectrum")
    d.redraw()
    return d


def _centre(designer, tag):
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements[tag].position)
    return int((x0 + x1) / 2), int((y0 + y1) / 2)


def _hover(designer, tag=None, point=None):
    x, y = point if point else _centre(designer, tag)
    designer._on_hover(_Motion(x, y))
    return designer._tag_tip


# -- what it says ----------------------------------------------------------


def test_hovering_a_button_names_its_tag(designer):
    tip = _hover(designer, "run_fit")
    assert tip.text == "tag: run_fit"


@pytest.mark.parametrize(
    "kind, tag",
    [("label", "lbl_0"), ("text_box", "edt_0"), ("number_box", "val_0")],
)
def test_every_text_element_is_named(designer, kind, tag):
    designer.create_element(kind, Rect(0.55, 0.55, 0.30, 0.15))
    designer.redraw()
    assert _hover(designer, tag).text == f"tag: {tag}"


def test_a_selector_is_named_too(designer):
    """It shows "Select a File", so its tag is hidden like any other caption."""
    designer.create_element("file_select", Rect(0.55, 0.20, 0.30, 0.15))
    designer.redraw()
    assert _hover(designer, "fileselect").text == "tag: fileselect"


def test_an_axes_is_not_named(designer):
    """It already has its tag drawn on it; a tooltip would only repeat it."""
    assert _hover(designer, "spectrum").text == ""


def test_empty_canvas_names_nothing(designer):
    assert _hover(designer, point=(390, 10)).text == ""


def test_moving_from_one_element_to_another_renames_it(designer):
    designer.create_element("label", Rect(0.55, 0.55, 0.30, 0.15))
    designer.redraw()
    assert _hover(designer, "run_fit").text == "tag: run_fit"
    assert _hover(designer, "lbl_0").text == "tag: lbl_0"


def test_leaving_an_element_clears_it(designer):
    assert _hover(designer, "run_fit").text == "tag: run_fit"
    assert _hover(designer, point=(390, 10)).text == ""


# -- when it appears -------------------------------------------------------


def test_it_is_faster_than_the_chrome_tooltips(designer):
    """The pointer is already on the thing being asked about."""
    assert FAST_DELAY_MS < DELAY_MS
    assert designer._tag_tip.delay_ms == FAST_DELAY_MS


def test_it_waits_rather_than_flashing_on_every_pass(designer):
    """Zero delay would flicker across the canvas on any pointer movement."""
    tip = _hover(designer, "run_fit")
    assert tip.visible is False, "it should be scheduled, not shown immediately"
    assert designer._tag_tip.delay_ms > 0


def test_it_does_appear_once_the_wait_is_over(designer):
    tip = _hover(designer, "run_fit")
    tip._pop()
    assert tip.visible is True


def test_hovering_the_same_element_does_not_restart_the_wait(designer):
    """Otherwise it would never appear while the pointer drifts by a pixel."""
    tip = _hover(designer, "run_fit")
    tip._pop()
    _hover(designer, "run_fit")
    assert tip.visible is True, "a second hover on the same element hid it again"


def test_pressing_hides_it(designer):
    tip = _hover(designer, "run_fit")
    tip._pop()
    x, y = _centre(designer, "run_fit")
    designer._on_press(_Motion(x, y))
    designer._on_release(_Motion(x, y))
    assert tip.visible is False


def test_dragging_does_not_leave_it_hanging(designer):
    tip = _hover(designer, "run_fit")
    tip._pop()
    x, y = _centre(designer, "run_fit")
    designer._on_press(_Motion(x, y))
    designer._on_hover(_Motion(x + 20, y + 20))
    assert tip.visible is False
    designer._on_release(_Motion(x + 20, y + 20))


def test_a_synthesised_event_without_root_coordinates_still_works(designer):
    """Tk supplies x_root; a test-made event does not, and neither should break."""
    designer._on_hover(_Motion(*_centre(designer, "run_fit")))
    assert designer._tag_tip.text == "tag: run_fit"


def test_a_renamed_element_reports_its_new_tag(designer):
    element = designer.layout.elements["run_fit"]
    designer.apply_properties(
        "run_fit", tag="fit", position=element.position, label=element.label
    )
    designer.redraw()
    assert _hover(designer, "fit").text == "tag: fit"
