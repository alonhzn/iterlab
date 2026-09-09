"""Schema rules: names, geometry, uniqueness."""

import pytest

from iterlab.errors import NameInUse, NameInvalid
from iterlab.layout.schema import (
    DEFAULT_INTERACTION,
    Element,
    Layout,
    Rect,
    validate_tag,
)


@pytest.mark.parametrize("name", ["spectrum", "run_fit", "a", "x2", "ax_0"])
def test_valid_names_accepted(name):
    assert validate_tag(name) == name


@pytest.mark.parametrize(
    "name, reason",
    [
        ("class", "python keyword"),
        ("import", "python keyword"),
        ("2fast", "starts with a digit"),
        ("has space", "not an identifier"),
        ("has-dash", "not an identifier"),
        ("", "empty"),
        ("_private", "underscore is reserved for iterlab"),
    ],
)
def test_unusable_names_rejected(name, reason):
    with pytest.raises(NameInvalid):
        validate_tag(name)


def test_duplicate_name_rejected():
    with pytest.raises(NameInUse):
        validate_tag("ax_0", existing={"ax_0": object()})


def test_rect_rejects_out_of_bounds():
    with pytest.raises(ValueError):
        Rect(left=0.8, bottom=0.1, width=0.5, height=0.2)  # past the right edge
    with pytest.raises(ValueError):
        Rect(left=0.1, bottom=0.9, width=0.2, height=0.5)  # past the top edge
    with pytest.raises(ValueError):
        Rect(left=-0.1, bottom=0.1, width=0.2, height=0.2)
    with pytest.raises(ValueError):
        Rect(left=0.1, bottom=0.1, width=0.0, height=0.2)


def test_rect_rounds_to_two_decimals():
    """One part in a hundred of the window - finer than that is noise."""
    r = Rect(0.123456, 0.2, 0.3, 0.4)
    assert r.as_list() == [0.12, 0.2, 0.3, 0.4]


def test_rounding_happens_on_construction_not_only_on_save():
    """So what is in memory is what is on disk, always."""
    r = Rect(0.123456, 0.51234, 0.31111, 0.4)
    assert (r.left, r.bottom, r.width) == (0.12, 0.51, 0.31)


def test_a_sliver_becomes_the_smallest_real_element(): 
    """Rounding must not turn a thin element into an invalid one."""
    r = Rect(0.5, 0.5, 0.004, 0.004)
    assert r.width == 0.01 and r.height == 0.01


def test_rounding_never_pushes_an_element_off_the_window():
    """Rounding out and away from the origin could cross the far edge."""
    r = Rect(0.996, 0.996, 0.004, 0.004)
    assert r.left + r.width <= 1.0
    assert r.bottom + r.height <= 1.0


def test_handler_naming_convention():
    e = Element("spectrum", "axes", Rect(0.1, 0.1, 0.5, 0.5))
    assert e.handler_name("clicked") == "on_clicked_spectrum"
    assert e.handler_name("motion") == "on_motion_spectrum"
    assert set(e.all_handler_names()) == {
        "on_clicked_spectrum",
        "on_hover_spectrum",
        "on_motion_spectrum",
        "on_key_spectrum",
        # Renaming an element has to carry this one too, or a box's handler
        # would be orphaned by a rename.
        "on_changed_spectrum",
    }


def test_default_interaction_is_click_for_both_types():
    assert DEFAULT_INTERACTION["button"] == "clicked"
    assert DEFAULT_INTERACTION["axes"] == "clicked"


def test_layout_add_rejects_duplicates():
    layout = Layout()
    layout.add(Element("a", "button", Rect(0, 0, 0.1, 0.1)))
    with pytest.raises(NameInUse):
        layout.add(Element("a", "button", Rect(0.2, 0, 0.1, 0.1)))


def test_next_name_skips_taken():
    layout = Layout()
    layout.add(Element("cmd_0", "button", Rect(0, 0, 0.1, 0.1)))
    layout.add(Element("button_1", "button", Rect(0.2, 0, 0.1, 0.1)))
    assert layout.next_tag("button") == "cmd_1"
    assert layout.next_tag("axes") == "ax_0"


def test_retag_preserves_order():
    layout = Layout()
    for n in ("a", "b", "c"):
        layout.add(Element(n, "button", Rect(0, 0, 0.1, 0.1)))
    layout.retag("b", "middle")
    assert layout.tags() == ["a", "middle", "c"]
    assert layout.elements["middle"].tag == "middle"


def test_empty_layout_reports_empty():
    assert Layout().is_empty
