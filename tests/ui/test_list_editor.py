"""Drawing a list in the editor: its options, its preview, its stub."""

import pytest

from iterlab.layout import store
from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    app.built.create_element("list", Rect(0.1, 0.1, 0.4, 0.5))
    return app.built


def test_a_new_list_is_lst_0_with_a_click_stub(editor):
    assert "lst_0" in editor.layout.elements
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_clicked_lst_0(ev" in source
    assert "event.index" in source and "ev.lst_0.append" in source


def test_both_options_are_offered_up_front(editor):
    panel = editor.properties
    assert "multi_select" in panel._entries and "scroll_x" in panel._entries
    assert not panel.advanced_open, "they are basic, not in the drawer"
    assert "label" not in panel._entries, "a list has no caption"


def test_ticking_an_option_saves_it(editor):
    panel = editor.properties
    panel._entries["multi_select"].set(True)
    panel._commit()
    assert editor.layout.elements["lst_0"].multi_select
    assert store.load(editor.interface.layout_path).elements["lst_0"].multi_select
    panel._entries["scroll_x"].set(True)
    panel._commit()
    assert store.load(editor.interface.layout_path).elements["lst_0"].scroll_x


def test_the_row_colour_is_in_the_drawer(editor):
    panel = editor.properties
    assert "highlight" in panel._entries
    panel._entries["highlight"].delete(0, "end")
    panel._entries["highlight"].insert(0, "#fff4d6")
    panel._commit()
    assert editor.layout.elements["lst_0"].style.highlight == "#fff4d6"


def test_it_looks_like_a_list_on_the_canvas(editor):
    """Placeholder rows, since the real ones only exist once code adds them."""
    editor.app.root.update()
    x0, y0, x1, y1 = editor._to_pixels(editor.layout.elements["lst_0"].position)
    inside = editor.canvas.find_enclosed(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    bars = [i for i in inside if editor.canvas.type(i) == "rectangle"
            and editor.canvas.coords(i)[3] - editor.canvas.coords(i)[1] < 12]
    assert len(bars) >= 3


def test_the_palette_offers_it(editor):
    from iterlab.ui.palette import DISPLAY_NAME

    assert DISPLAY_NAME["list"] == "List"
