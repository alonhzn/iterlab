"""The in-window fault signal (FR-033, FR-033a, FR-033b)."""

import time

import pytest

from iterlab.app import open_interface
from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(make_app):
    app = make_app()
    d = app.built
    d.create_element("button", Rect(0.05, 0.1, 0.25, 0.12), name="run_fit")
    d.create_element("button", Rect(0.4, 0.1, 0.25, 0.12), name="other")
    yield app


def _code(app, text):
    time.sleep(0.01)
    app.interface.code_path.write_text(text, encoding="utf-8")


def test_banner_hidden_when_nothing_is_wrong(gui):
    _code(gui, "def on_clicked_run_fit(ev, event):\n    ev.ok = True\n")
    gui.toggle()
    gui.built.handles["run_fit"].widget.invoke()
    assert gui.built.banner.visible is False


def test_banner_names_the_failed_element(gui):
    _code(gui, "def on_clicked_run_fit(ev, event):\n    raise ValueError('nope')\n")
    gui.toggle()
    gui.built.handles["run_fit"].widget.invoke()
    banner = gui.built.banner
    assert banner.visible is True
    assert "run_fit" in banner.text and "nope" in banner.text


def test_other_elements_stay_usable_while_a_fault_shows(gui):
    """FR-033a: non-blocking. Nothing has to be dismissed."""
    _code(
        gui,
        "def on_clicked_run_fit(ev, event):\n    raise ValueError('nope')\n"
        "def on_clicked_other(ev, event):\n    ev.other_ran = True\n",
    )
    gui.toggle()
    gui.built.handles["run_fit"].widget.invoke()
    assert gui.built.banner.visible is True

    gui.built.handles["other"].widget.invoke()
    assert gui.built.ev.other_ran is True


def test_banner_clears_once_corrected_code_runs(gui):
    """FR-033b: the window must not accumulate stale warnings."""
    _code(gui, "def on_clicked_run_fit(ev, event):\n    raise ValueError('nope')\n")
    gui.toggle()
    gui.built.handles["run_fit"].widget.invoke()
    assert gui.built.banner.visible is True

    _code(gui, "def on_clicked_run_fit(ev, event):\n    ev.fixed = True\n")
    gui.built.handles["run_fit"].widget.invoke()
    assert gui.built.banner.visible is False
    assert gui.built.ev.fixed is True


def test_window_opens_even_when_code_is_broken_at_launch(gui):
    """FR-032: a broken file is never a reason not to open."""
    _code(gui, "def on_startup(ev)\n    pass\n")
    gui.toggle()
    assert gui.built is not None
    assert gui.built.banner.visible is True
