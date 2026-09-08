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
    designer.create_element("axes", Rect(0.05, 0.35, 0.9, 0.6), tag="spectrum")
    designer.create_element("button", Rect(0.05, 0.1, 0.25, 0.12), tag="run_fit")


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
    # tk.Button or ttk.Button - the test is about a clickable control existing,
    # not about which widget class draws it.
    from tkinter import ttk

    buttons = [
        w for w in app.chrome.winfo_children()
        if isinstance(w, (app.tk.Button, ttk.Button))
        and "Restart" not in str(w.cget("text"))
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


def test_the_session_survives_a_mode_switch(app):
    """A layout tweak must not cost a data reload.

    This inverts the earlier behaviour. The session used to be torn down on
    every switch, which did not remove the reload cost so much as move it from
    "every code edit" to "every layout edit".
    """
    _draw_two(app)
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.data = list(range(500))\n", encoding="utf-8"
    )
    app.toggle()
    data = app.built.ev.data
    assert len(data) == 500

    app.toggle()          # into the editor
    app.toggle()          # and back
    assert app.built.ev.data is data, "the same object, not merely an equal one"


def test_startup_runs_once_per_session_not_once_per_visit(app):
    _draw_two(app)
    app.interface.code_path.write_text(
        "COUNT = []\n"
        "def on_startup(ev):\n    COUNT.append(1)\n    ev.runs = len(COUNT)\n",
        encoding="utf-8",
    )
    app.toggle()
    assert app.built.ev.runs == 1
    for _ in range(3):
        app.toggle()
        app.toggle()
    assert app.built.ev.runs == 1, "startup re-ran on a toggle"


def test_restarting_the_session_applies_a_startup_change(app):
    """Toggling now preserves, so there must be one explicit way to start over."""
    _draw_two(app)
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.marker = 'first'\n", encoding="utf-8"
    )
    app.toggle()
    assert app.built.ev.marker == "first"

    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.marker = 'second'\n", encoding="utf-8"
    )
    app.toggle()
    app.toggle()
    assert app.built.ev.marker == "first", "a toggle must not re-run startup"

    app.restart_session()
    assert app.built.ev.marker == "second", "restart re-ran the edited startup"


def test_a_restart_discards_the_researchers_data(app):
    """That is precisely the difference between restarting and toggling."""
    _draw_two(app)
    app.interface.code_path.write_text(
        "def on_startup(ev):\n    ev.data = [1, 2, 3]\n", encoding="utf-8"
    )
    app.toggle()
    before = app.built.ev.data
    app.restart_session()
    assert app.built.ev.data is not before


def test_toggle_is_chrome_and_never_in_the_layout(app):
    """FR-015c: it is not an element and cannot be reached from researcher code."""
    _draw_two(app)
    assert "toggle" not in app.interface.layout.tags()
    layout_text = app.interface.layout_path.read_text(encoding="utf-8")
    assert "toggle" not in layout_text

    app.toggle()
    assert "toggle" not in app.built.ev._element_handles()
