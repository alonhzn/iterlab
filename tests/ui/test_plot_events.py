"""Clicking, hovering and typing on a plot area.

These go through matplotlib's own callback machinery — the closures in
`build_plot_area` — rather than calling `dispatcher.invoke` directly. That
distinction matters: a NameError inside those closures survived a full suite
because every other plot test drove the dispatcher and never the wiring.
"""

import pytest
from matplotlib.backend_bases import KeyEvent, MouseEvent

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

RECORD = """
def on_startup(ev):
    ev.seen = []
    ev.spectrum.plot([0, 1, 2], [0, 1, 4])

def on_clicked_spectrum(ev, event):
    ev.seen.append(("clicked", event.tag, event.button, event.x is not None))

def on_motion_spectrum(ev, event):
    ev.seen.append(("motion", event.tag))

def on_key_spectrum(ev, event):
    ev.seen.append(("key", event.tag, event.key))
"""


@pytest.fixture
def gui(mapped, make_app):
    app = make_app()
    app.built.create_element("plot_area", Rect(0.1, 0.1, 0.8, 0.8), tag="spectrum")
    app.interface.code_path.write_text(RECORD, encoding="utf-8")
    app.toggle()
    app.root.update()
    app.built.handles["spectrum"].canvas.draw()
    return app


def _inside(handle, data_x=1.0, data_y=1.0):
    """A display-space point that lands inside the axes."""
    x, y = handle.axes.transData.transform((data_x, data_y))
    return int(x), int(y)


def _fire(handle, event):
    handle.canvas.callbacks.process(event.name, event)


def test_clicking_a_plot_reaches_the_handler(gui):
    handle = gui.built.handles["spectrum"]
    x, y = _inside(handle)
    _fire(handle, MouseEvent("button_press_event", handle.canvas, x, y, button=1))
    gui.root.update()

    clicks = [e for e in gui.built.ev.seen if e[0] == "clicked"]
    assert clicks, "a click on the plot never reached the researcher's handler"
    assert clicks[0][1] == "spectrum"


def test_a_plot_click_carries_data_coordinates(gui):
    """The whole reason plot events come from matplotlib rather than Tk."""
    handle = gui.built.handles["spectrum"]
    x, y = _inside(handle, 1.0, 1.0)
    _fire(handle, MouseEvent("button_press_event", handle.canvas, x, y, button=1))
    gui.root.update()

    clicked = next(e for e in gui.built.ev.seen if e[0] == "clicked")
    assert clicked[3] is True, "event.x was None; coordinates were lost"


@pytest.mark.parametrize("button, expected", [(1, "left"), (2, "middle"), (3, "right")])
def test_every_mouse_button_is_reported_on_a_plot(gui, button, expected):
    handle = gui.built.handles["spectrum"]
    x, y = _inside(handle)
    _fire(handle, MouseEvent("button_press_event", handle.canvas, x, y, button=button))
    gui.root.update()

    clicked = next(e for e in gui.built.ev.seen if e[0] == "clicked")
    assert clicked[2] == expected


def test_moving_over_a_plot_reaches_the_handler(gui):
    handle = gui.built.handles["spectrum"]
    x, y = _inside(handle)
    _fire(handle, MouseEvent("motion_notify_event", handle.canvas, x, y))
    gui.root.update()
    assert any(e[0] == "motion" for e in gui.built.ev.seen)


def test_a_key_press_on_a_plot_reaches_the_handler(gui):
    handle = gui.built.handles["spectrum"]
    x, y = _inside(handle)
    _fire(handle, KeyEvent("key_press_event", handle.canvas, "a", x, y))
    gui.root.update()

    keys = [e for e in gui.built.ev.seen if e[0] == "key"]
    assert keys and keys[0][2] == "a"


def test_a_click_outside_the_axes_is_ignored(gui):
    """The toolbar and the frame around the axes are not the plot."""
    handle = gui.built.handles["spectrum"]
    _fire(handle, MouseEvent("button_press_event", handle.canvas, 1, 1, button=1))
    gui.root.update()
    assert not [e for e in gui.built.ev.seen if e[0] == "clicked"]
