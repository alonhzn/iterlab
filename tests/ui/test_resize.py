"""Geometry scales with the window; text does not (FR-021a, FR-021b)."""

import pytest

from iterlab.layout.schema import Rect
from iterlab.ui.elements import BASE_FONT_SIZE

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(make_app):
    app = make_app()
    d = app.built
    d.create_element("button", Rect(0.10, 0.20, 0.30, 0.15), tag="go")
    d.create_element("axes", Rect(0.10, 0.50, 0.80, 0.40), tag="spectrum")
    app.toggle()
    app.root.update_idletasks()
    return app


@pytest.mark.parametrize("size", ["400x300", "800x600", "1600x900"])
def test_proportions_hold_at_every_window_size(gui, size):
    gui.root.geometry(size)
    gui.root.update()
    info = gui.built.handles["go"].widget.place_info()
    assert float(info["relx"]) == pytest.approx(0.10, abs=1e-3)
    assert float(info["relwidth"]) == pytest.approx(0.30, abs=1e-3)
    assert float(info["relheight"]) == pytest.approx(0.15, abs=1e-3)


def test_pixel_size_actually_grows_with_the_window(gui):
    """Proportional in fact, not merely in the `place` options.

    Needs a mapped window: an unmapped one reports stale widget geometry however
    often you resize it.
    """
    gui.root.deiconify()
    try:
        gui.root.geometry("400x300")
        gui.root.update()
        small = gui.built.handles["go"].widget.winfo_width()

        gui.root.geometry("1200x800")
        gui.root.update()
        large = gui.built.handles["go"].widget.winfo_width()
    finally:
        gui.root.withdraw()

    assert large > small * 2, (
        f"geometry must scale with the window, got {small}px then {large}px"
    )


def test_font_size_is_fixed_and_does_not_scale(gui):
    """The exemption that keeps text readable at both extremes."""
    widget = gui.built.handles["go"].widget
    import tkinter.font as tkfont

    for size in ("400x300", "1600x900"):
        gui.root.geometry(size)
        gui.root.update()
        font = tkfont.Font(font=widget.cget("font"))
        assert abs(font.cget("size")) == BASE_FONT_SIZE
