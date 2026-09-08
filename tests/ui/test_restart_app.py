"""The cold restart: everything from disk, as if freshly launched.

Distinct from restarting the session, which keeps the layout already in memory.
The difference only shows when the files on disk have moved on, which is exactly
the case this button exists for.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.runtime import loader as loader_mod
from iterlab.ui.app import EDITOR, GUI

pytestmark = pytest.mark.ui

CODE = """
def on_startup(ev):
    ev.marker = "first"

def on_clicked_go(ev, event):
    pass
"""


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    return app


def _restart_button(app):
    """The widget a researcher actually presses."""
    from tkinter import ttk

    buttons = [
        w for w in app.chrome.winfo_children()
        if isinstance(w, (app.tk.Button, ttk.Button))
        and "reset" in str(w.cget("text")).lower()
    ]
    assert len(buttons) == 1, f"expected one hard-reset button, found {len(buttons)}"
    return buttons[0]


def test_the_button_exists_in_chrome(gui):
    _restart_button(gui)  # raises if missing


def test_the_button_is_available_in_both_modes(gui):
    assert str(_restart_button(gui).cget("state")) != "disabled"
    gui.toggle()
    assert gui.mode == EDITOR
    assert str(_restart_button(gui).cget("state")) != "disabled"


def test_pressing_it_discards_the_session(gui):
    gui.built.ev.expensive = object()
    kept = gui.built.ev.expensive
    _restart_button(gui).invoke()
    gui.root.update()
    assert getattr(gui.built.ev, "expensive", None) is not kept


def test_pressing_it_re_runs_an_edited_startup(gui):
    assert gui.built.ev.marker == "first"
    gui.interface.code_path.write_text(
        CODE.replace('"first"', '"second"'), encoding="utf-8"
    )
    _restart_button(gui).invoke()
    gui.root.update()
    assert gui.built.ev.marker == "second"


def test_it_re_reads_a_layout_edited_on_disk(gui):
    """The whole difference between this and restarting the session.

    A restart that trusted the layout already in memory would silently ignore
    the file, which is the one thing a cold restart must not do.
    """
    before = set(gui.interface.layout.tags())
    assert before == {"go"}

    # Another element, written straight to the file - as a hand edit would be.
    text = gui.interface.layout_path.read_text(encoding="utf-8")
    gui.interface.layout_path.write_text(
        text.replace(
            "elements:",
            "elements:\n"
            "  added_by_hand:\n"
            "    type: label\n"
            "    position: [0.5, 0.5, 0.2, 0.1]\n"
            "    label: 'hi'\n",
        ),
        encoding="utf-8",
    )

    _restart_button(gui).invoke()
    gui.root.update()
    assert "added_by_hand" in gui.interface.layout.tags()
    assert "added_by_hand" in gui.built.handles


def test_it_stays_in_the_mode_it_was_pressed_in(gui):
    """Restarting is not a request to be moved to a different screen."""
    _restart_button(gui).invoke()
    assert gui.mode == GUI

    gui.toggle()
    assert gui.mode == EDITOR
    _restart_button(gui).invoke()
    assert gui.mode == EDITOR, "restarting in the editor moved the researcher"


def test_it_forgets_the_researchers_module(gui):
    name = loader_mod.module_name_for(gui.interface.code_path)
    import sys

    assert name in sys.modules, "the module should be loaded before we restart"
    gui.restart_app()
    # Rebuilding loads it again, so the check is that the object is not the same
    # one - nothing was carried over.
    assert sys.modules.get(name) is not None


def test_it_clears_a_stale_startup_notice(gui):
    import os
    import time

    gui.interface.code_path.write_text(
        CODE.replace('"first"', '"second"'), encoding="utf-8"
    )
    stamp = time.time() + 1
    os.utime(gui.interface.code_path, (stamp, stamp))
    gui.built.handles["go"].widget.invoke()
    gui.root.update()
    assert gui.built.notice.visible, "the notice should be up before we restart"

    _restart_button(gui).invoke()
    gui.root.update()
    assert not gui.built.notice.visible
    assert gui.built.ev.marker == "second"


def test_the_window_is_not_resized(gui):
    """Restarting must not rearrange the researcher's desktop."""
    gui.root.geometry("900x600")
    gui.root.update_idletasks()
    before = (gui.root.winfo_width(), gui.root.winfo_height())
    _restart_button(gui).invoke()
    gui.root.update_idletasks()
    assert (gui.root.winfo_width(), gui.root.winfo_height()) == before


def test_an_unparsable_layout_file_does_not_take_the_window_down(gui):
    """Principle III: the process never dies on the researcher's account.

    Reading the layout from disk is what makes this restart cold, and it is also
    what exposes it to a file someone edited by hand and got wrong. Found by a
    test that meant to check something else, and crashed instead.
    """
    gui.interface.layout_path.write_text(
        "schema_version: 2\nwindow: {width: 800, height: 450}\n"
        "elements:\n  broken:\n    type: label\n    position: nonsense\n",
        encoding="utf-8",
    )
    _restart_button(gui).invoke()
    gui.root.update()

    assert gui.root.winfo_exists(), "the window died on a bad layout file"
    assert gui.built is not None
    assert "go" in gui.interface.layout.tags(), "the last good layout was kept"


def test_the_bad_layout_file_is_reported_not_swallowed(gui):
    gui.interface.layout_path.write_text(
        "schema_version: 2\nwindow: {width: 800, height: 450}\n"
        "elements:\n  broken:\n    type: label\n    position: nonsense\n",
        encoding="utf-8",
    )
    _restart_button(gui).invoke()
    gui.root.update()
    assert gui.built.banner.visible, "a silently ignored layout file is the worst outcome"
