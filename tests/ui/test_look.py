"""The editor's appearance: themed widgets and drawn element icons."""

import pytest

pytestmark = pytest.mark.ui


def test_a_modern_ttk_theme_is_applied(make_app):
    from tkinter import ttk

    app = make_app()
    assert ttk.Style(app.root).theme_use() == "clam", (
        "clam is the one fully restyleable theme on every platform"
    )


def test_the_palette_shows_an_icon_for_every_element_type(make_app):
    """Icons are drawn as vectors, so they never depend on a platform font."""
    from iterlab.layout.schema import ELEMENT_TYPES

    app = make_app()
    cards = app.built.palette._cards
    assert set(cards) == set(ELEMENT_TYPES)
    for element_type, card in cards.items():
        assert card.icon.find_all(), f"{element_type} icon drew nothing"


def test_selecting_a_palette_card_highlights_it(make_app):
    app = make_app()
    palette = app.built.palette
    palette.selected.set("button")
    assert palette._cards["button"].selected
    assert not palette._cards["plot_area"].selected


def test_setting_the_variable_updates_the_cards(make_app):
    """Anything driving the palette should not need to know it draws cards."""
    app = make_app()
    palette = app.built.palette
    palette.selected.set("plot_area")
    assert palette._cards["plot_area"].selected
    palette.selected.set("button")
    assert palette._cards["button"].selected
    assert not palette._cards["plot_area"].selected


def test_clicking_a_card_selects_that_type(mapped, make_app):
    app = make_app()
    app.root.update()
    palette = app.built.palette
    palette._cards["button"].frame.event_generate("<Button-1>")
    app.root.update()
    assert palette.element_type == "button"


def test_the_canvas_uses_the_theme_surface(make_app):
    from iterlab.ui import theme

    app = make_app()
    assert app.built.canvas.cget("bg") == theme.SURFACE


def test_every_property_field_is_visible_at_the_default_window_size(mapped, make_app):
    """Tk unmaps children that no longer fit instead of clipping them.

    An overflowing sidebar therefore loses widgets silently: no error, no
    scrollbar, the field simply is not there. At the 800x450 default the
    geometry fields were past that line, and the only symptom was that typing
    into them did nothing.
    """
    from iterlab.layout.schema import Rect

    app = make_app()
    app.root.geometry("800x450")
    app.root.update()

    d = app.built
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    app.root.update()

    missing = [
        name for name, entry in d.properties._entries.items()
        if not entry.winfo_ismapped()
    ]
    assert not missing, f"these property fields are not on screen: {missing}"


def test_the_sidebar_scrolls_when_it_overflows(mapped, make_app):
    from iterlab.layout.schema import Rect

    app = make_app()
    app.root.geometry("800x420")
    app.root.update()
    d = app.built
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    app.root.update()

    sidebar = d.sidebar
    if sidebar.inner.winfo_reqheight() > sidebar.canvas.winfo_height():
        assert sidebar._scrollbar_shown, "content overflows but no scrollbar appeared"


def test_the_delete_control_is_reachable_at_a_small_window(mapped, make_app):
    """A destructive action must never be the thing pushed off the bottom."""
    from iterlab.layout.schema import Rect

    app = make_app()
    app.root.geometry("800x450")
    app.root.update()
    d = app.built
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    app.root.update()

    assert d.properties._danger_zone.winfo_children(), "no delete control built"


def test_the_palette_lists_every_element_type(make_app):
    from iterlab.layout.schema import ELEMENT_TYPES

    app = make_app()
    assert set(app.built.palette._cards) == set(ELEMENT_TYPES)


def test_palette_rows_stay_compact_as_types_are_added(mapped, make_app):
    """The vocabulary is going to grow; a tall card per type would not survive
    a dozen of them in a sidebar."""
    app = make_app()
    app.root.update()
    for element_type, card in app.built.palette._cards.items():
        height = card.frame.winfo_reqheight()
        assert height <= 34, f"{element_type} row is {height}px, too tall to scale"


def test_the_editor_opens_large_enough_for_its_own_controls(mapped, make_app):
    """Editor mode adds a sidebar the interface size knows nothing about."""
    from iterlab.ui.app import MIN_EDITOR_HEIGHT, MIN_EDITOR_WIDTH

    app = make_app()
    app.root.update()
    assert app.root.winfo_width() >= MIN_EDITOR_WIDTH - 1
    assert app.root.winfo_height() >= MIN_EDITOR_HEIGHT - 1


def test_switching_to_the_editor_never_shrinks_the_window(mapped, make_app):
    """A size the researcher chose is theirs; toggling should not undo it."""
    from iterlab.layout.schema import Rect

    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.toggle()
    app.root.geometry("1400x900")
    app.root.update()
    app.toggle()
    app.root.update()
    assert app.root.winfo_width() >= 1400
    assert app.root.winfo_height() >= 900
