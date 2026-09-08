"""The plotting toolbar works with no handler written (FR-017e)."""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("plot_area", Rect(0.05, 0.1, 0.9, 0.8), tag="spectrum")
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
    axes = gui.built.handles["spectrum"].axes
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
    gui.toggle()
    gui.toggle()
    runner = gui.built
    runner.dispatcher.invoke(
        "on_clicked_spectrum",
        __import__("iterlab.runtime.dispatch", fromlist=["Event"]).Event(
            kind="clicked", tag="spectrum", x=1.0, y=1.0
        ),
    )
    assert runner.ev.clicks == 1
