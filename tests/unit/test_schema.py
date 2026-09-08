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


@pytest.mark.parametrize("name", ["spectrum", "run_fit", "a", "x2", "plot_0"])
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
        validate_tag("plot_0", existing={"plot_0": object()})


def test_rect_rejects_out_of_bounds():
    with pytest.raises(ValueError):
        Rect(left=0.8, bottom=0.1, width=0.5, height=0.2)  # past the right edge
    with pytest.raises(ValueError):
        Rect(left=0.1, bottom=0.9, width=0.2, height=0.5)  # past the top edge
    with pytest.raises(ValueError):
        Rect(left=-0.1, bottom=0.1, width=0.2, height=0.2)
    with pytest.raises(ValueError):
        Rect(left=0.1, bottom=0.1, width=0.0, height=0.2)


def test_rect_rounds_for_readable_diffs():
    r = Rect(0.123456, 0.2, 0.3, 0.4)
    assert r.as_list()[0] == 0.1235


def test_handler_naming_convention():
    e = Element("spectrum", "plot_area", Rect(0.1, 0.1, 0.5, 0.5))
    assert e.handler_name("clicked") == "on_clicked_spectrum"
    assert e.handler_name("motion") == "on_motion_spectrum"
    assert set(e.all_handler_names()) == {
        "on_clicked_spectrum",
        "on_hover_spectrum",
        "on_motion_spectrum",
        "on_key_spectrum",
    }


def test_default_interaction_is_click_for_both_types():
    assert DEFAULT_INTERACTION["button"] == "clicked"
    assert DEFAULT_INTERACTION["plot_area"] == "clicked"


def test_layout_add_rejects_duplicates():
    layout = Layout()
    layout.add(Element("a", "button", Rect(0, 0, 0.1, 0.1)))
    with pytest.raises(NameInUse):
        layout.add(Element("a", "button", Rect(0.2, 0, 0.1, 0.1)))


def test_next_name_skips_taken():
    layout = Layout()
    layout.add(Element("button_0", "button", Rect(0, 0, 0.1, 0.1)))
    layout.add(Element("button_1", "button", Rect(0.2, 0, 0.1, 0.1)))
    assert layout.next_tag("button") == "button_2"
    assert layout.next_tag("plot_area") == "plot_0"


def test_retag_preserves_order():
    layout = Layout()
    for n in ("a", "b", "c"):
        layout.add(Element(n, "button", Rect(0, 0, 0.1, 0.1)))
    layout.retag("b", "middle")
    assert layout.tags() == ["a", "middle", "c"]
    assert layout.elements["middle"].tag == "middle"


def test_empty_layout_reports_empty():
    assert Layout().is_empty
