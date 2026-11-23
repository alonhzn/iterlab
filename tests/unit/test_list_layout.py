"""A list in the layout: how it looks and behaves is drawn, its rows are not."""

import pytest

from iterlab.layout import store
from iterlab.layout.schema import Element, Layout, Rect, Style, style_fields_for


def _list(**options):
    return Element("lst_0", "list", Rect(0.1, 0.1, 0.3, 0.4), **options)


def test_it_is_tagged_lst():
    assert Layout().next_tag("list") == "lst_0"


def test_its_options_start_off():
    element = _list()
    assert not element.multi_select and not element.scroll_x


def test_only_a_list_has_them():
    with pytest.raises(ValueError):
        Element("go", "button", Rect(0.1, 0.1, 0.2, 0.1), multi_select=True)
    with pytest.raises(ValueError):
        Element("go", "button", Rect(0.1, 0.1, 0.2, 0.1), scroll_x=True)


def test_it_has_no_caption():
    with pytest.raises(ValueError):
        _list(label="rows")


def test_it_takes_the_text_styles_and_a_row_highlight():
    fields = style_fields_for("list")
    for name in ("font", "font_size", "bold", "italic", "text_color", "highlight"):
        assert name in fields
    assert "highlight" not in style_fields_for("button")


def test_a_bad_highlight_is_refused():
    with pytest.raises(ValueError):
        Style(highlight="not a colour!")


def test_it_round_trips(tmp_path):
    layout = Layout()
    layout.add(_list(multi_select=True, scroll_x=True,
                     style=Style(highlight="#fff4d6", bold=True)))
    path = tmp_path / "demo_layout.py"
    store.save(layout, path)
    again = store.load(path).elements["lst_0"]
    assert again.multi_select and again.scroll_x
    assert again.style.highlight == "#fff4d6" and again.style.bold


def test_options_left_off_are_not_written(tmp_path):
    layout = Layout()
    layout.add(_list())
    path = tmp_path / "demo_layout.py"
    store.save(layout, path)
    text = path.read_text(encoding="utf-8")
    assert "multi_select" not in text and "scroll_x" not in text
    assert "'lst_0': {'type': 'list'" in text


def test_a_list_is_declared_for_the_editor(tmp_path):
    layout = Layout()
    layout.add(_list())
    path = tmp_path / "demo_layout.py"
    store.save(layout, path)
    assert 'lst_0: "List"' in path.read_text(encoding="utf-8")


def test_an_option_that_is_not_true_or_false_is_refused(tmp_path):
    path = tmp_path / "demo_layout.py"
    path.write_text(
        "LAYOUT = {'schema_version': 8, 'elements': {'lst_0': {'type': 'list', "
        "'position': [0.1, 0.1, 0.3, 0.4], 'multi_select': 'yes'}}}\n",
        encoding="utf-8",
    )
    from iterlab.errors import LayoutInvalid

    with pytest.raises(LayoutInvalid, match="multi_select"):
        store.load(path)


def test_setting_the_options():
    layout = Layout()
    layout.add(_list())
    layout.set_list_options("lst_0", multi_select=True)
    assert layout.elements["lst_0"].multi_select and not layout.elements["lst_0"].scroll_x
    layout.set_list_options("lst_0", scroll_x=True)
    assert layout.elements["lst_0"].multi_select and layout.elements["lst_0"].scroll_x
