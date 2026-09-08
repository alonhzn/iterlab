"""Editing style in the panel, and overriding it from code."""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(mapped, make_app):
    app = make_app()
    d = app.built
    d.create_element("label", Rect(0.1, 0.6, 0.4, 0.08), tag="title")
    d.create_element("button", Rect(0.1, 0.3, 0.15, 0.08), tag="go")
    d.select("title")
    app.root.update()
    return d


def _set(panel, field, value):
    widget = panel._entries[field]
    if hasattr(widget, "set") and not hasattr(widget, "delete"):
        widget.set(value)          # BooleanVar / StringVar
    elif hasattr(widget, "current"):
        widget.set(value)          # Combobox
    else:
        widget.delete(0, "end")
        widget.insert(0, str(value))
    return panel.apply()


# -- the editor sets the starting appearance --------------------------------


def test_a_colour_typed_in_the_panel_is_saved(editor):
    assert _set(editor.properties, "background", "#ff5533") is True
    assert editor.layout.elements["title"].style.background == "#ff5533"


def test_an_invalid_colour_is_rejected_and_reported(editor):
    before = editor.layout.elements["title"].style
    assert _set(editor.properties, "background", "#nothex") is False
    assert editor.layout.elements["title"].style == before
    assert editor.properties._message.cget("text") != ""


def test_font_size_and_weight_are_saved(editor):
    _set(editor.properties, "font_size", 18)
    _set(editor.properties, "bold", True)
    style = editor.layout.elements["title"].style
    assert style.font_size == 18
    assert style.bold is True


def test_alignment_is_saved(editor):
    _set(editor.properties, "align", "left")
    assert editor.layout.elements["title"].style.align == "left"


def test_the_font_dropdown_offers_installed_families_only(editor):
    from iterlab.ui import theme

    offered = list(editor.properties._entries["font"].cget("values"))
    assert offered[0] == "(default)"
    assert offered == theme.available_fonts(editor.properties.frame)


def test_style_is_persisted_to_the_layout_file(editor):
    from iterlab.layout import store

    _set(editor.properties, "background", "#123456")
    saved = store.load(editor.interface.layout_path)
    assert saved.elements["title"].style.background == "#123456"


def test_styling_never_touches_the_code_file(editor):
    """Principle II: appearance is layout, not code."""
    before = editor.interface.code_path.read_bytes()
    _set(editor.properties, "background", "#abcdef")
    _set(editor.properties, "bold", True)
    assert editor.interface.code_path.read_bytes() == before


def test_a_axes_offers_no_colour_fields(editor):
    editor.create_element("axes", Rect(0.5, 0.5, 0.3, 0.3), tag="spectrum")
    editor.select("spectrum")
    assert "background" not in editor.properties._entries
    assert "visible" in editor.properties._entries


# -- code overrides it at run time ------------------------------------------


def test_the_editor_supplies_the_starting_appearance(editor):
    editor.layout.restyle("title", background="#fff4d6", bold=True, font_size=16)
    editor.interface.save_layout()
    editor.app.toggle()
    editor.app.root.update()

    handle = editor.app.built.handles["title"]
    assert handle.widget.cget("bg") == "#fff4d6"
    assert handle.bold is True


def test_code_overrides_what_the_editor_set(editor):
    editor.layout.restyle("title", background="#fff4d6")
    editor.interface.save_layout()
    editor.interface.code_path.write_text(
        "def on_startup(ev):\n"
        "    ev.title.background = '#ffe0e0'\n"
        "    ev.title.text_color = '#a01020'\n"
        "    ev.title.font_size = 20\n",
        encoding="utf-8",
    )
    editor.app.toggle()
    editor.app.root.update()

    widget = editor.app.built.handles["title"].widget
    assert widget.cget("bg") == "#ffe0e0"
    assert widget.cget("fg") == "#a01020"


def test_a_code_override_never_writes_back_to_the_layout(editor):
    """The layout is the starting state, not a live mirror of the session."""
    editor.layout.restyle("title", background="#fff4d6")
    editor.interface.save_layout()
    before = editor.interface.layout_path.read_bytes()

    editor.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.title.background = '#000000'\n", encoding="utf-8"
    )
    editor.app.toggle()
    editor.app.root.update()

    assert editor.interface.layout_path.read_bytes() == before


def test_enabled_and_visible_are_settable_from_code(editor):
    editor.interface.code_path.write_text(
        "def on_startup(ev):\n"
        "    ev.go.enabled = False\n"
        "    ev.title.visible = False\n",
        encoding="utf-8",
    )
    editor.app.toggle()
    editor.app.root.update()

    assert editor.app.built.handles["go"].widget.cget("state") == "disabled"
    assert not editor.app.built.handles["title"].widget.winfo_ismapped()


def test_a_style_property_reads_back_what_was_set(editor):
    editor.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.title.italic = True\n", encoding="utf-8"
    )
    editor.app.toggle()
    editor.app.root.update()
    assert editor.app.built.handles["title"].italic is True


def test_the_canvas_previews_the_element_style(editor):
    """Choosing a colour must be judgeable in the editor, not only after a toggle."""
    editor.layout.restyle("title", background="#ff5533")
    editor.select("title")

    fills = [
        editor.canvas.itemcget(item, "fill")
        for item in editor.canvas.find_all()
        if editor.canvas.type(item) == "rectangle"
    ]
    assert "#ff5533" in fills, f"styled fill not drawn on the canvas: {fills}"


def test_an_unstyled_element_keeps_its_type_tint(editor):
    from iterlab.ui import theme

    fills = [
        editor.canvas.itemcget(item, "fill")
        for item in editor.canvas.find_all()
        if editor.canvas.type(item) == "rectangle"
    ]
    assert theme.ELEMENT_FILL["button"] in fills


def test_a_plot_style_property_can_be_read_back(editor):
    """Anything settable must be readable, or the API is a trap.

    A plot handle delegates unknown attributes to its matplotlib Axes, which
    knows nothing about `visible` - so reading it raised AttributeError while
    setting it worked fine.
    """
    editor.create_element("axes", Rect(0.5, 0.5, 0.3, 0.3), tag="spectrum")
    editor.app.toggle()
    editor.app.root.update()

    handle = editor.app.built.handles["spectrum"]
    assert handle.visible is True
    handle.visible = False
    assert handle.visible is False


def test_every_settable_style_property_is_also_readable(editor):
    editor.create_element("axes", Rect(0.5, 0.5, 0.3, 0.3), tag="spectrum")
    editor.app.toggle()
    editor.app.root.update()

    for tag in ("title", "go", "spectrum"):
        handle = editor.app.built.handles[tag]
        for prop in handle.STYLE_PROPERTIES:
            getattr(handle, prop)  # raises if a setter has no matching getter
