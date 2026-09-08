"""The mode toggle, exercised against a real Tk window.

This is the display-dependent tier of Gate 1. It stays small deliberately: the
constitutional guarantees are all proven headlessly, so a display problem in CI
blocks only this slice.
"""

import pytest

from iterlab.app import open_interface
from iterlab.layout.schema import Rect
from iterlab.ui.app import EDITOR, GUI

pytestmark = pytest.mark.ui


@pytest.fixture
def app(make_app):
    return make_app()


def _draw_two(app):
    designer = app.built
    designer.create_element("plot_area", Rect(0.05, 0.35, 0.9, 0.6), name="spectrum")
    designer.create_element("button", Rect(0.05, 0.1, 0.25, 0.12), name="run_fit")


def test_new_interface_opens_in_editor_mode(app):
    assert app.mode == EDITOR


def test_interface_with_elements_opens_in_gui_mode(make_app):
    first = make_app()
    _draw_two(first)
    first.close()

    second = make_app()
    assert second.mode == GUI


def test_toggle_switches_both_ways(app):
    _draw_two(app)
    assert app.toggle() == GUI
    assert app.toggle() == EDITOR
    assert app.toggle() == GUI


def _toggle_button(app):
    """Find the actual widget a researcher would click.

    Calling `app.toggle()` directly, as every other test here does, exercises
    the mode-switching logic but not the button that reaches it. This is the
    test that would have caught the toggle being defined but never
    instantiated — every other test passed while the button did not exist.
    """
    buttons = [
        w for w in app.chrome.winfo_children() if isinstance(w, app.tk.Button)
    ]
    assert len(buttons) == 1, f"expected exactly one toggle button in chrome, found {len(buttons)}"
    return buttons[0]


def test_a_real_button_exists_in_chrome(app):
    _toggle_button(app)  # raises if it is missing


def test_clicking_the_actual_button_switches_modes(app):
    _draw_two(app)
    assert app.mode == EDITOR
    _toggle_button(app).invoke()
    assert app.mode == GUI
    _toggle_button(app).invoke()
    assert app.mode == EDITOR


def test_button_label_reflects_the_current_mode_after_a_real_click(app):
    _draw_two(app)
    button = _toggle_button(app)
    before = button.cget("text")
    button.invoke()
    after = _toggle_button(app).cget("text")
    assert after != before, "the label must update to reflect the new mode"


def test_button_is_never_disabled(app):
    """The concrete complaint this bug produced: a toggle that looks dead."""
    _draw_two(app)
    for _ in range(3):
        button = _toggle_button(app)
        assert str(button.cget("state")) != "disabled"
        button.invoke()


def test_root_and_geometry_survive_a_switch(app):
    """One root for the whole process — a toggle, not a relaunch (R13)."""
    _draw_two(app)
    root_before = app.root
    app.root.geometry("900x500")
    app.root.update_idletasks()
    app.toggle()
    assert app.root is root_before
    assert app.root.winfo_width() > 1


def test_content_widgets_are_destroyed_not_hidden(app):
    """Hidden widgets keep live bindings that still fire (R13)."""
    _draw_two(app)
    app.toggle()
    editor_widgets = app.content.winfo_children()
    app.toggle()
    for widget in editor_widgets:
        assert not widget.winfo_exists(), "the old mode's widgets must be gone"


def test_session_ends_on_leaving_gui_mode(app):
    """FR-015d: ev and everything in it is discarded on a mode switch."""
    _draw_two(app)
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.data = list(range(500))\n", encoding="utf-8"
    )
    app.toggle()
    runner = app.built
    assert len(runner.ev.data) == 500

    app.toggle()
    assert runner.ev is None, "the session was torn down"


def test_switching_back_starts_a_fresh_session(app):
    """FR-015e: and that is what applies a startup change without relaunching."""
    _draw_two(app)
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.marker = 'first'\n", encoding="utf-8"
    )
    app.toggle()
    assert app.built.ev.marker == "first"

    app.toggle()
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.marker = 'second'\n", encoding="utf-8"
    )
    app.toggle()
    assert app.built.ev.marker == "second", "the edited startup ran in the new session"


def test_toggle_is_chrome_and_never_in_the_layout(app):
    """FR-015c: it is not an element and cannot be reached from researcher code."""
    _draw_two(app)
    assert "toggle" not in app.interface.layout.names()
    layout_text = app.interface.layout_path.read_text(encoding="utf-8")
    assert "toggle" not in layout_text

    app.toggle()
    assert "toggle" not in app.built.ev._element_handles()
