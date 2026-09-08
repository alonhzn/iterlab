"""Advanced properties live behind a "More" drawer.

The panel is the first thing a researcher meets after drawing something, and a
wall of eleven fields buries the two that matter. What stays visible is what you
had to decide to have made the element at all; everything else is a refinement.
"""

import pytest

from iterlab.layout.schema import Rect, basic_properties

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    app.built.create_element("button", Rect(0.25, 0.25, 0.2, 0.2), tag="go")
    app.built.create_element("axes", Rect(0.5, 0.5, 0.3, 0.3), tag="ax_0")
    app.built.select("go")
    return app.built


def _mapped(widget):
    widget.update_idletasks()
    return bool(widget.winfo_ismapped())


def test_the_drawer_starts_closed(editor):
    assert editor.properties.advanced_open is False
    assert not _mapped(editor.properties._advanced)


def test_the_basic_properties_are_visible_without_opening_it(editor):
    panel = editor.properties
    assert _mapped(panel._entries["tag"]), "tag is always basic"
    assert _mapped(panel._entries["label"]), "a button's caption is basic"


def test_the_advanced_properties_are_hidden(editor):
    panel = editor.properties
    for field in ("left", "bottom", "width", "height", "background", "font_size"):
        assert not _mapped(panel._entries[field]), f"{field} should be behind the drawer"


def test_opening_it_reveals_them(editor):
    panel = editor.properties
    panel.toggle_advanced()
    assert panel.advanced_open is True
    assert _mapped(panel._advanced)
    assert _mapped(panel._entries["left"])


def test_clicking_the_header_opens_it(editor):
    """Through the widget a researcher actually clicks, not the method."""
    panel = editor.properties
    panel._drawer_label.event_generate("<Button-1>")
    panel._drawer_label.update()
    assert panel.advanced_open is True


def test_the_label_says_what_pressing_it_will_do(editor):
    panel = editor.properties
    assert panel._drawer_label.cget("text") == "More"
    panel.toggle_advanced()
    assert panel._drawer_label.cget("text") == "Less"


def test_the_arrow_is_drawn_and_flips(editor):
    """Drawn, not a glyph character - a missing glyph renders as a hollow box."""
    panel = editor.properties
    closed = panel._drawer_arrow.coords(panel._drawer_arrow.find_all()[0])
    panel.toggle_advanced()
    opened = panel._drawer_arrow.coords(panel._drawer_arrow.find_all()[0])
    assert closed != opened, "the arrow must point the other way when open"


def test_it_stays_open_when_another_element_is_selected(editor):
    """Someone adjusting colours across elements should not have to reopen it."""
    panel = editor.properties
    panel.toggle_advanced()
    editor.select("ax_0")
    assert panel.advanced_open is True
    assert _mapped(panel._advanced)


def test_it_stays_closed_by_default_across_selections(editor):
    editor.select("ax_0")
    assert editor.properties.advanced_open is False


def test_an_axes_has_no_basic_label(editor):
    """matplotlib decides how an axes looks, so it has nothing basic but a tag."""
    editor.select("ax_0")
    panel = editor.properties
    assert "label" not in panel._entries
    assert _mapped(panel._entries["tag"])


def test_advanced_values_are_still_committed_when_never_opened(editor):
    """The fields exist whether or not they were revealed.

    Nothing about applying an edit may depend on which widgets the researcher
    happened to look at.
    """
    panel = editor.properties
    entry = panel._entries["width"]
    entry.delete(0, "end")
    entry.insert(0, "0.4")
    panel.apply()
    assert editor.layout.elements["go"].position.width == pytest.approx(0.4)


def test_the_basic_set_is_declared_per_type_not_hardcoded():
    """A slider will declare its range the same way a button declares its caption."""
    assert basic_properties("button") == ("label",)
    assert basic_properties("axes") == ()
    assert basic_properties("a_type_that_does_not_exist_yet") == ()
