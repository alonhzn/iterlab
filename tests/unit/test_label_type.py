"""The label element: text on screen, with no generated handler."""

import pytest

from iterlab.codegen import templates
from iterlab.layout.schema import (
    DEFAULT_INTERACTION,
    DEFAULT_SIZE,
    ELEMENT_TYPES,
    TEXT_TYPES,
    Element,
    Rect,
)


def _element(type_, name="thing", label=""):
    return Element(name, type_, Rect(0.1, 0.1, 0.2, 0.2), label=label)


def test_label_is_a_known_element_type():
    assert "label" in ELEMENT_TYPES


def test_a_label_carries_text():
    assert "label" in TEXT_TYPES
    assert _element("label", label="Signal to noise").label == "Signal to noise"


def test_a_axes_still_cannot_carry_text():
    with pytest.raises(ValueError):
        _element("axes", label="nope")


def test_a_label_has_no_default_interaction():
    """It displays text and is set from code. A generated click handler for
    every label would leave a pile of dead functions in the researcher's file."""
    assert DEFAULT_INTERACTION["label"] is None


def test_no_stub_is_generated_for_a_label():
    assert templates.default_stub(_element("label")) is None


def test_stubs_are_still_generated_for_the_other_types():
    for type_ in ("button", "axes"):
        assert templates.default_stub(_element(type_)) is not None


def test_every_interaction_is_still_available_on_a_label():
    """Only the automatic stub is withheld, not the capability (FR-017a)."""
    element = _element("label", name="title")
    assert element.handler_name("clicked") == "on_clicked_title"
    assert "on_motion_title" in element.all_handler_names()


def test_appending_a_stub_for_a_label_writes_nothing(tmp_path):
    from iterlab.codegen import inject

    path = tmp_path / "demo.py"
    original = "def on_startup(ev):\n    pass\n"
    path.write_text(original, encoding="utf-8")

    element = _element("label", name="title")
    assert inject.append_stub(path, element, templates.default_stub(element)) is False
    assert path.read_text(encoding="utf-8") == original


def test_every_type_has_a_default_size_and_a_name_prefix():
    from iterlab.layout.schema import TAG_PREFIX

    for element_type in ELEMENT_TYPES:
        assert element_type in DEFAULT_SIZE
        assert element_type in TAG_PREFIX
        assert element_type in DEFAULT_INTERACTION


def test_a_maximised_button_is_not_absurdly_large():
    """The whole point of shrinking it: 1920x1080 is the common case."""
    width, height = DEFAULT_SIZE["button"]
    assert 100 <= width * 1920 <= 170, "button too wide on a maximised window"
    assert 28 <= height * 1080 <= 48, "button too tall on a maximised window"
