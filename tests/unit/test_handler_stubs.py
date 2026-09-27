"""Handlers beyond the default one: which exist per type, and writing them.

The editor's right-click menu lists every interaction an element can fire and
writes the one asked for. Creating an element still writes only its default
stub (FR-017d); these are written on request, one at a time.
"""

import ast

import pytest

from iterlab.codegen import inject, templates
from iterlab.layout.schema import ELEMENT_TYPES, Element, Rect


def _element(kind, tag="thing"):
    return Element(tag, kind, Rect(0.1, 0.1, 0.2, 0.2))


def test_the_default_comes_first():
    assert _element("button").interactions[0] == "clicked"
    assert _element("text_box").interactions[0] == "changed"
    assert _element("number_box").interactions[0] == "changed"


def test_only_a_box_offers_changed():
    """`changed` means a value was committed; a button never commits one."""
    for kind in ELEMENT_TYPES:
        offered = "changed" in _element(kind).interactions
        assert offered == (kind in ("text_box", "number_box")), kind


def test_only_what_takes_the_keyboard_offers_key():
    """A click never gives a button, selector or label the keyboard."""
    for kind in ELEMENT_TYPES:
        offered = "key" in _element(kind).interactions
        assert offered == (kind in ("axes", "text_box", "number_box")), kind


def test_every_type_offers_click_hover_and_motion():
    for kind in ELEMENT_TYPES:
        assert {"clicked", "hover", "motion"} <= set(_element(kind).interactions)


def test_a_label_has_no_main_handler_and_lists_the_rest_in_order():
    assert _element("label").interactions == ("clicked", "hover", "motion")


def test_nothing_is_listed_twice():
    for kind in ELEMENT_TYPES:
        offered = _element(kind).interactions
        assert len(offered) == len(set(offered)), kind


@pytest.mark.parametrize("kind", ELEMENT_TYPES)
def test_every_offered_handler_has_a_stub_that_parses(kind):
    element = _element(kind)
    for interaction in element.interactions:
        stub = templates.stub_for(element, interaction)
        names = [n.name for n in ast.parse(stub).body if isinstance(n, ast.FunctionDef)]
        assert names == [element.handler_name(interaction)], (kind, interaction)


def test_the_default_stub_is_the_one_creation_writes():
    element = _element("button")
    assert templates.stub_for(element, "clicked") == templates.default_stub(element)


@pytest.fixture
def code(tmp_path):
    path = tmp_path / "demo.py"
    templates.write_starter_file(path, "demo")
    return path


def test_an_optional_handler_is_appended(code):
    element = _element("button", "go")
    written = inject.append_stub(code, element, templates.stub_for(element, "hover"), "hover")
    assert written
    assert "on_hover_go" in inject.top_level_function_names(code.read_text(encoding="utf-8"))


def test_it_is_not_appended_twice(code):
    element = _element("button", "go")
    stub = templates.stub_for(element, "hover")
    inject.append_stub(code, element, stub, "hover")
    assert not inject.append_stub(code, element, stub, "hover")
    assert code.read_text(encoding="utf-8").count("def on_hover_go") == 1


def test_it_lands_above_the_launcher(code):
    element = _element("button", "go")
    inject.append_stub(code, element, templates.stub_for(element, "motion"), "motion")
    text = code.read_text(encoding="utf-8")
    assert text.index("def on_motion_go") < text.index('if __name__ == "__main__":')


def test_a_label_can_have_one_written_on_request(code):
    """No default stub for a label, but asking for one works."""
    element = _element("label", "status")
    assert inject.append_stub(code, element, templates.stub_for(element, "clicked"), "clicked")
