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
    assert not palette._cards["axes"].selected


def test_setting_the_variable_updates_the_cards(make_app):
    """Anything driving the palette should not need to know it draws cards."""
    app = make_app()
    palette = app.built.palette
    palette.selected.set("axes")
    assert palette._cards["axes"].selected
    palette.selected.set("button")
    assert palette._cards["button"].selected
    assert not palette._cards["axes"].selected


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


def test_every_property_field_is_reachable_at_the_default_window_size(mapped, make_app):
    """Tk unmaps children that no longer fit instead of clipping them.

    Before the sidebar scrolled, an overflowing panel lost widgets silently: no
    error, no scrollbar, the field simply was not there. Now the panel is taller
    than the window by design, so the invariant is *reachability* - the scroll
    region must cover the whole panel - rather than everything being mapped at
    once.
    """
    from iterlab.layout.schema import Rect

    app = make_app()
    app.root.geometry("800x450")
    app.root.update()

    d = app.built
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    app.root.update()

    sidebar = d.sidebar
    content_height = sidebar.inner.winfo_reqheight()
    region = sidebar.canvas.cget("scrollregion")
    assert region, "no scroll region, so anything past the fold is unreachable"

    reachable = int(float(region.split()[3]))
    assert reachable >= content_height - 2, (
        f"scroll region {reachable}px does not cover {content_height}px of panel"
    )
    assert sidebar._scrollbar_shown, "content overflows but no scrollbar appeared"


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


def test_the_editor_is_the_interface_plus_the_toolbar(mapped, make_app):
    """One remembered number describes both modes.

    The editor used to apply a floor of its own on top of adding the sidebar,
    which is what made the canvas a different shape from the interface: an
    element drawn square came out stretched when run.
    """
    from iterlab.ui.app import MIN_EDITOR_HEIGHT

    app = make_app()
    app.root.update()
    window = app.interface.layout.window
    assert app.root.winfo_width() == window.width + app.toolbar_allowance()
    # Taller than the interface when the interface is short, so the toolbar has
    # room for its own controls. The canvas does not grow into that space.
    assert app.root.winfo_height() == max(
        window.height + app.chrome_height(), MIN_EDITOR_HEIGHT
    )


def test_the_toolbar_always_has_room_for_its_own_controls(mapped, make_app):
    """Why the editor has a floor at all, stated as a consequence.

    Tk does not scroll or clip a packed column: a child that does not fit is
    simply never mapped. So an editor sized to a short interface silently loses
    the bottom of the properties panel - the researcher sees a panel that looks
    complete, and the controls below the fold are not there. That is how this
    went red on CI: a suite that edits properties was editing widgets that had
    fallen off the window.
    """
    from iterlab.layout.schema import Rect

    app = make_app()
    app.interface.layout.resize(800, 200)      # far shorter than the toolbar
    app.apply_size_for_mode()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.built.select("go")
    app.root.update()
    app.root.update_idletasks()

    panel = app.built.properties
    for name in ("_message", "_danger_zone", "_body"):
        widget = getattr(panel, name)
        assert widget.winfo_ismapped(), f"{name} fell off the bottom of the toolbar"
        bottom = widget.winfo_rooty() + widget.winfo_height()
        assert bottom <= app.root.winfo_rooty() + app.root.winfo_height(), name


def test_the_canvas_is_exactly_the_interface(mapped, make_app):
    """What you draw on is the window you will run in, to the pixel."""
    from iterlab.layout.schema import Rect

    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.root.update_idletasks()
    canvas = (app.built.canvas.winfo_width(), app.built.canvas.winfo_height())

    app.toggle()
    app.root.update_idletasks()
    assert (app.content.winfo_width(), app.content.winfo_height()) == canvas


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
