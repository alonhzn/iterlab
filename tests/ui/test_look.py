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


def test_both_modes_are_the_same_window(mapped, make_app):
    """One remembered number, one window. Switching resizes nothing.

    The editor used to be the interface *plus* the toolbar beside it, so every
    switch changed the window width - and every plot on screen re-rendered for
    it. The toolbar now takes its room from inside the window instead.
    """
    app = make_app()
    app.root.update()
    in_editor = (app.root.winfo_width(), app.root.winfo_height())

    app.toggle()
    app.root.update()
    assert (app.root.winfo_width(), app.root.winfo_height()) == in_editor

    app.toggle()
    app.root.update()
    assert (app.root.winfo_width(), app.root.winfo_height()) == in_editor


def test_the_window_is_the_interface_plus_the_top_bar(mapped, make_app):
    app = make_app()
    app.root.update()
    window = app.interface.layout.window
    assert app.root.winfo_width() == window.width
    assert app.root.winfo_height() == window.height + app.chrome_height()


def test_the_sidebar_scrolls_rather_than_losing_its_lower_half(mapped, make_app):
    """Both windows are one size, so a short one leaves the toolbar short too.

    Tk does not clip a packed column - it stops mapping the children that do
    not fit, and they are gone with no error anywhere. The sidebar is a
    scrolling column for exactly that reason, and this is the test that says
    so: at a window too short for it, every control is still there and the
    scrollbar can reach them.
    """
    from iterlab.layout.schema import Rect

    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.built.select("go")
    app.root.geometry("700x320")
    app.root.update()
    app.root.update_idletasks()

    sidebar = app.built.sidebar
    assert sidebar.inner.winfo_reqheight() > sidebar.canvas.winfo_height(), (
        "this test is meaningless unless the toolbar really is too tall here"
    )
    first, last = sidebar.canvas.yview()
    assert last < 1.0, "the column is not scrollable, so the rest is unreachable"

    panel = app.built.properties
    for name in ("_message", "_danger_zone", "_body"):
        assert getattr(panel, name).winfo_ismapped(), f"{name} was dropped, not scrolled"


def test_the_canvas_has_the_interface_s_proportions(mapped, make_app):
    """Not its pixels any more - its shape.

    Positions are fractions, so what has to survive the trip from canvas to
    window is the *ratio*. An element drawn square on a canvas of a different
    shape would come out stretched when it ran, which is the whole reason the
    canvas is not simply given whatever room is left.
    """
    from iterlab.layout.schema import Rect

    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.root.update()
    app.root.update_idletasks()

    canvas = app.built.canvas
    area_width, area_height = app.interface_size()
    drawn = canvas.winfo_width() / canvas.winfo_height()
    interface = area_width / area_height
    assert abs(drawn - interface) < 0.02, f"canvas {drawn:.3f} vs interface {interface:.3f}"


def test_the_canvas_fits_inside_the_room_beside_the_toolbar(mapped, make_app):
    app = make_app()
    app.root.update()
    app.root.update_idletasks()
    canvas, stage = app.built.canvas, app.built.stage
    assert canvas.winfo_width() <= stage.winfo_width()
    assert canvas.winfo_height() <= stage.winfo_height()


def test_the_canvas_is_centred_in_that_room(mapped, make_app):
    """The leftover shows as backdrop on both sides, not all on one."""
    app = make_app()
    app.root.update()
    app.root.update_idletasks()
    canvas, stage = app.built.canvas, app.built.stage
    left = canvas.winfo_x()
    right = stage.winfo_width() - (left + canvas.winfo_width())
    top = canvas.winfo_y()
    bottom = stage.winfo_height() - (top + canvas.winfo_height())
    assert abs(left - right) <= 1, f"{left} left, {right} right"
    assert abs(top - bottom) <= 1, f"{top} top, {bottom} bottom"


def test_the_backdrop_is_not_the_canvas_colour(mapped, make_app):
    """The canvas is a picture of the run window; its edge has to be findable."""
    from iterlab.ui import theme

    app = make_app()
    assert app.built.stage.cget("bg") != app.built.canvas.cget("bg")
    assert app.built.stage.cget("bg") == theme.STAGE


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
