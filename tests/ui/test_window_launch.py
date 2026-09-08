"""GUI mode against a real window: placement, clicking, startup order."""

import pytest

from iterlab.app import open_interface
from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CODE = """import numpy as np

def on_startup(ev):
    ev.order = ["startup"]
    ev.x = np.linspace(0, 1, 50)
    ev.spectrum.plot(ev.x, ev.x ** 2)

def on_clicked_run_fit(ev, event):
    ev.order.append(("clicked", event.button))
"""


@pytest.fixture
def gui(make_app):
    app = make_app()
    designer = app.built
    designer.create_element("axes", Rect(0.05, 0.35, 0.9, 0.6), tag="spectrum")
    designer.create_element("button", Rect(0.05, 0.1, 0.25, 0.12), tag="run_fit")
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    app.root.update_idletasks()
    yield app


def test_both_elements_are_realized(gui):
    assert set(gui.built.handles) == {"spectrum", "run_fit"}


def test_startup_ran_before_any_interaction(gui):
    assert gui.built.ev.order == ["startup"]
    assert len(gui.built.ev.x) == 50


def test_clicking_the_button_runs_the_handler(gui):
    gui.built.handles["run_fit"].widget.invoke()
    assert gui.built.ev.order[-1] == ("clicked", "left")


def test_elements_are_placed_proportionally(gui):
    """Geometry comes straight from the normalized layout (FR-021a)."""
    gui.root.geometry("800x600")
    gui.root.update()
    info = gui.built.handles["run_fit"].widget.place_info()
    assert float(info["relx"]) == pytest.approx(0.05, abs=1e-3)
    assert float(info["relwidth"]) == pytest.approx(0.25, abs=1e-3)


def test_plot_handle_exposes_the_matplotlib_axes(gui):
    """Researchers use the API they already know, not an iterlab one."""
    handle = gui.built.handles["spectrum"]
    assert hasattr(handle, "plot") and hasattr(handle, "set_title")
    handle.set_title("works")
    assert handle.get_title() == "works"


def test_axes_has_the_navigation_toolbar(gui):
    """Pan and zoom with no handler written (FR-017e)."""
    frame = gui.built.handles["spectrum"].widget
    kinds = [type(c).__name__ for c in frame.winfo_children()]
    assert any("Toolbar" in k for k in kinds), kinds


def test_button_caption_comes_from_the_layout(gui):
    """Whatever the layout says is what the widget shows - default or edited."""
    assert gui.built.handles["run_fit"].text == "Click here!", "the default caption"

    gui.toggle()
    element = gui.built.layout.elements["run_fit"]
    gui.built.apply_properties("run_fit", position=element.position, label="Run fit")
    gui.toggle()
    assert gui.built.handles["run_fit"].text == "Run fit"


def test_missing_handler_click_is_silent(gui):
    """An element with no code behind it does nothing, and says nothing."""
    gui.built.handles["spectrum"].figure.canvas.draw()
    assert gui.built.banner.visible is False


def test_plotting_in_a_handler_actually_repaints(gui):
    """`ev.plot.plot(...)` must reach the screen.

    An embedded figure gets no automatic redraw: pyplot installs that hook, and
    pyplot has no place here because `plt.show()` would start a second event
    loop against Tk's. `stale` is matplotlib's own "changed since last draw"
    flag, so asserting it is False is asserting a repaint happened.
    """
    gui.interface.code_path.write_text(
        "def on_startup(ev):\n"
        "    ev.spectrum.plot([0, 1, 2], [0, 1, 4])\n"
        "def on_clicked_run_fit(ev, event):\n"
        "    ev.spectrum.clear()\n"
        "    ev.spectrum.plot([0, 1, 2], [4, 1, 0])\n",
        encoding="utf-8",
    )
    gui.toggle()
    gui.toggle()  # fresh session so the new startup runs
    gui.root.update()

    figure = gui.built.handles["spectrum"].figure
    assert not figure.stale, "startup's plot was never painted"

    gui.built.handles["run_fit"].widget.invoke()
    gui.root.update()
    assert not figure.stale, "the handler's plot was never painted"


def test_a_handler_that_draws_nothing_costs_no_repaint(gui):
    """Motion handlers fire continuously; only stale figures are redrawn."""
    gui.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.spectrum.plot([0, 1], [0, 1])\n"
        "def on_clicked_run_fit(ev, event):\n    ev.counter = 1\n",
        encoding="utf-8",
    )
    gui.toggle()
    gui.toggle()
    gui.root.update()

    figure = gui.built.handles["spectrum"].figure
    gui.built.handles["run_fit"].widget.invoke()
    assert not figure.stale
    assert gui.built.ev.counter == 1
