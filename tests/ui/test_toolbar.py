"""The plotting toolbar works with no handler written (FR-017e)."""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("axes", Rect(0.05, 0.1, 0.9, 0.8), tag="spectrum")
    # Deliberately no handlers at all: the toolbar must not depend on them.
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.spectrum.plot([0, 1, 2], [0, 1, 4])\n",
        encoding="utf-8",
    )
    app.toggle()
    app.root.update_idletasks()
    return app


def test_toolbar_is_present_without_any_handler(gui):
    frame = gui.built.handles["spectrum"].widget
    toolbars = [c for c in frame.winfo_children() if "Toolbar" in type(c).__name__]
    assert toolbars, "a plot area carries the standard navigation toolbar"


def test_toolbar_offers_pan_and_zoom(gui):
    frame = gui.built.handles["spectrum"].widget
    toolbar = next(c for c in frame.winfo_children() if "Toolbar" in type(c).__name__)
    assert hasattr(toolbar, "pan") and hasattr(toolbar, "zoom")


def test_zoom_changes_the_view_without_researcher_code(gui):
    axes = gui.built.handles["spectrum"]
    before = axes.get_xlim()
    axes.set_xlim(0.5, 1.5)
    gui.built.handles["spectrum"].canvas.draw()
    assert axes.get_xlim() != before


def test_toolbar_does_not_swallow_the_researchers_click_handler(gui):
    """The toolbar must not consume interactions when it is not in use."""
    gui.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.clicks = 0\n"
        "def on_clicked_spectrum(ev, event):\n    ev.clicks += 1\n",
        encoding="utf-8",
    )
    # A restart, not a toggle: toggling preserves the session, so the edited
    # startup above would not run.
    gui.restart_session()
    runner = gui.built
    runner.dispatcher.invoke(
        "on_clicked_spectrum",
        __import__("iterlab.runtime.dispatch", fromlist=["Event"]).Event(
            kind="clicked", tag="spectrum", x=1.0, y=1.0
        ),
    )
    assert runner.ev.clicks == 1


# -- and it is actually on screen, under every plot ------------------------
#
# The tests above ask whether the toolbar widget exists. It did exist, under
# every plot, while being invisible under most of them - Tk hands out a frame's
# space in the order things are packed, and the canvas was packed first with
# expand=True, so it took the lot and the toolbar was silently never mapped.
# Whether it showed came down to whether the plot happened to be tall enough.


CODE = """def on_startup(ev):
    for tag in ("tall", "short", "wide"):
        getattr(ev, tag).plot([0, 1, 2], [0, 1, 4])
"""


@pytest.fixture
def several(mapped, make_app):
    """Three plots of deliberately different heights."""
    app = make_app()
    app.built.create_element("axes", Rect(0.04, 0.58, 0.92, 0.38), tag="tall")
    app.built.create_element("axes", Rect(0.04, 0.30, 0.44, 0.22), tag="short")
    app.built.create_element("axes", Rect(0.52, 0.30, 0.44, 0.22), tag="wide")
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    app.root.update()
    app.root.update_idletasks()
    return app


def _toolbar(app, tag):
    return app.built.handles[tag].canvas.toolbar


def test_every_plot_has_its_toolbar_on_screen(several):
    """The reported bug: it appeared under one plot and not the others."""
    for tag in ("tall", "short", "wide"):
        toolbar = _toolbar(several, tag)
        assert toolbar.winfo_ismapped(), f"{tag} has a toolbar nobody can see"
        assert toolbar.winfo_height() > 1, f"{tag} toolbar is {toolbar.winfo_height()}px"


def test_the_shorter_plot_gets_one_too(several):
    """Height is what decided it before, so state that it no longer does."""
    tall, short = _toolbar(several, "tall"), _toolbar(several, "short")
    assert short.winfo_ismapped()
    assert short.winfo_height() == tall.winfo_height()


def test_the_plot_still_gets_the_rest_of_the_space(several):
    """The toolbar takes its row; the canvas must take everything left."""
    for tag in ("tall", "short", "wide"):
        handle = several.built.handles[tag]
        frame = handle.widget
        canvas = handle.canvas.get_tk_widget()
        toolbar = _toolbar(several, tag)
        assert canvas.winfo_height() > toolbar.winfo_height(), (
            f"{tag}: canvas {canvas.winfo_height()}px under a "
            f"{toolbar.winfo_height()}px toolbar"
        )
        assert canvas.winfo_height() + toolbar.winfo_height() == frame.winfo_height()


def test_a_toolbar_survives_a_mode_switch(several):
    """The rebuild takes the same path, so it has to come back mapped."""
    several.toggle()
    several.root.update()
    several.toggle()
    several.root.update()
    several.root.update_idletasks()
    for tag in ("tall", "short", "wide"):
        assert _toolbar(several, tag).winfo_ismapped(), tag


# -- a pan or zoom survives a trip to the editor (was Gate 2 #19) -------------
#
# Decided 2026-09-26: it should. Rearranging a button must not throw away the
# view someone spent a minute zooming into. Both halves of it: the limits on
# the plot, and the toolbar's history of them, which is what Home and Back walk.


def _zoom(app, tag, xlim, ylim):
    """What the toolbar does for a zoom or a pan: record, change, record."""
    toolbar = _toolbar(app, tag)
    axes = app.built.handles[tag]
    if toolbar._nav_stack() is None:
        toolbar.push_current()  # the view before the first change is "home"
    axes.set_xlim(*xlim)
    axes.set_ylim(*ylim)
    toolbar.push_current()


def _round_trip(app):
    app.toggle()
    app.root.update()
    app.toggle()
    app.root.update()


def _limits(app, tag):
    axes = app.built.handles[tag]
    return tuple(axes.get_xlim()), tuple(axes.get_ylim())


def test_the_zoomed_view_survives_a_trip_to_the_editor(gui):
    _zoom(gui, "spectrum", (0.5, 1.5), (0.2, 2.0))
    _round_trip(gui)
    assert _limits(gui, "spectrum") == ((0.5, 1.5), (0.2, 2.0))


def test_home_still_goes_home_after_the_trip(gui):
    home = _limits(gui, "spectrum")
    _zoom(gui, "spectrum", (0.5, 1.5), (0.2, 2.0))
    _round_trip(gui)

    _toolbar(gui, "spectrum").home()
    assert _limits(gui, "spectrum") == home


def test_back_and_forward_still_walk_the_history_after_the_trip(gui):
    home = _limits(gui, "spectrum")
    _zoom(gui, "spectrum", (0.5, 1.5), (0.2, 2.0))
    _zoom(gui, "spectrum", (0.8, 1.2), (0.5, 1.5))
    _round_trip(gui)

    toolbar = _toolbar(gui, "spectrum")
    toolbar.back()
    assert _limits(gui, "spectrum") == ((0.5, 1.5), (0.2, 2.0))
    toolbar.back()
    assert _limits(gui, "spectrum") == home
    toolbar.forward()
    assert _limits(gui, "spectrum") == ((0.5, 1.5), (0.2, 2.0))


# -- the zoom tool itself, across the trip -------------------------------------
#
# Found by hand: with the zoom tool pressed, a trip to the editor left the old
# toolbar connected to the plot, still in zoom mode. Every drag afterwards made
# it draw on a canvas that no longer existed - a TclError per drag - while the
# new toolbar showed no tool pressed. The old toolbar lingers in a reference
# cycle in the real application, so these hold on to it the same way; a test
# that let it be collected passed against the bug.


def _drag(app, tag, start, end):
    """A left-button drag across the plot, in fractions of the canvas."""
    from matplotlib.backend_bases import MouseButton, MouseEvent

    canvas = app.built.handles[tag].canvas
    width, height = canvas.get_width_height()
    points = [(start[0] * width, start[1] * height), (end[0] * width, end[1] * height)]
    MouseEvent("button_press_event", canvas, *points[0], button=1)._process()
    try:
        # The button is held during the move; a zoom that sees otherwise
        # assumes the release was missed and abandons itself.
        moving = MouseEvent("motion_notify_event", canvas, *points[1],
                            buttons={MouseButton.LEFT})
    except TypeError:  # an older matplotlib, which does not check
        moving = MouseEvent("motion_notify_event", canvas, *points[1], button=1)
    moving._process()
    MouseEvent("button_release_event", canvas, *points[1], button=1)._process()


@pytest.fixture
def raised(gui):
    """Exceptions matplotlib would otherwise print and swallow."""
    caught = []
    figure = gui.built.handles["spectrum"].figure
    figure._canvas_callbacks.exception_handler = caught.append
    return caught


def test_the_zoom_tool_is_still_pressed_after_the_trip(gui):
    _toolbar(gui, "spectrum").zoom()
    _round_trip(gui)
    assert _toolbar(gui, "spectrum").mode.name == "ZOOM"


def test_the_pan_tool_is_still_pressed_after_the_trip(gui):
    _toolbar(gui, "spectrum").pan()
    _round_trip(gui)
    assert _toolbar(gui, "spectrum").mode.name == "PAN"


def test_no_tool_stays_no_tool(gui):
    _round_trip(gui)
    assert _toolbar(gui, "spectrum").mode.name == "NONE"


def test_zooming_after_the_trip_works_and_raises_nothing(mapped, gui, raised):
    old = _toolbar(gui, "spectrum")
    old.zoom()
    _round_trip(gui)
    gui.root.update()
    before = _limits(gui, "spectrum")

    _drag(gui, "spectrum", (0.3, 0.3), (0.6, 0.6))

    assert raised == [], f"the old toolbar answered the drag: {raised}"
    assert _limits(gui, "spectrum") != before, "the drag did not zoom"
    assert old is not None  # kept alive, as the application keeps it
