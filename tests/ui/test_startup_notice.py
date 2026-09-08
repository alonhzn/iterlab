"""The offer to re-run an edited `on_startup`.

Editing startup is the one edit that does nothing on the next click, because
the next click is not what runs it. These tests drive the actual widgets a
researcher presses rather than the methods behind them - the distinction that
has hidden every wiring defect in this project so far.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

STARTUP_V1 = """
def on_startup(ev):
    ev.marker = "first"
    ev.data = list(range(100))

def on_clicked_go(ev, event):
    ev.clicks = getattr(ev, "clicks", 0) + 1
"""

STARTUP_V2 = STARTUP_V1.replace('"first"', '"second"')
HANDLER_EDITED = STARTUP_V1.replace("+ 1", "+ 10")


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    app.interface.code_path.write_text(STARTUP_V1, encoding="utf-8")
    app.toggle()
    return app


def _click(app):
    app.built.handles["go"].widget.invoke()
    app.root.update()


def _edit(app, source):
    """Write the file so the loader cannot miss it.

    The stamp is (mtime_ns, size), so a same-size same-instant write is the one
    case it could miss - not worth risking in a test about noticing edits.
    """
    import os
    import time

    app.interface.code_path.write_text(source, encoding="utf-8")
    stamp = time.time() + 1
    os.utime(app.interface.code_path, (stamp, stamp))


def test_no_notice_when_nothing_was_edited(gui):
    _click(gui)
    assert not gui.built.notice.visible


def test_no_notice_when_only_a_handler_was_edited(gui):
    """The common edit. Crying wolf here would make the notice worthless."""
    _edit(gui, HANDLER_EDITED)
    _click(gui)
    assert not gui.built.notice.visible, "a handler edit must not claim startup is stale"


def test_editing_startup_raises_the_notice(gui):
    _edit(gui, STARTUP_V2)
    _click(gui)
    assert gui.built.notice.visible
    assert "on_startup" in gui.built.notice.text


def test_the_edit_alone_changes_nothing_until_asked(gui):
    """The notice offers; it does not act. Re-running is the researcher's call."""
    _edit(gui, STARTUP_V2)
    _click(gui)
    assert gui.built.ev.marker == "first", "startup re-ran without being asked"


def test_pressing_re_run_applies_the_edit(gui):
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.built.notice.rerun_button.invoke()
    gui.root.update()
    assert gui.built.ev.marker == "second"


def test_re_running_keeps_the_researchers_data(gui):
    """The whole reason to offer this instead of only offering a restart."""
    gui.built.ev.expensive = object()
    kept = gui.built.ev.expensive
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.built.notice.rerun_button.invoke()
    gui.root.update()
    assert gui.built.ev.expensive is kept, "re-running must not be a restart"


def test_the_notice_clears_once_startup_has_re_run(gui):
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.built.notice.rerun_button.invoke()
    gui.root.update()
    assert not gui.built.notice.visible
    _click(gui)
    assert not gui.built.notice.visible, "it came back with nothing further edited"


def test_dismissing_hides_it_without_running_anything(gui):
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.built.notice.dismiss_button.invoke()
    gui.root.update()
    assert not gui.built.notice.visible
    assert gui.built.ev.marker == "first"


def test_a_further_edit_after_dismissing_raises_it_again(gui):
    """Ignoring one edit must not make the next one silent."""
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.built.notice.dismiss_button.invoke()

    _edit(gui, STARTUP_V1.replace('"first"', '"third"'))
    _click(gui)
    assert gui.built.notice.visible


def test_a_restart_leaves_no_stale_notice(gui):
    _edit(gui, STARTUP_V2)
    _click(gui)
    gui.restart_session()
    gui.root.update()
    assert gui.built.ev.marker == "second"
    assert not gui.built.notice.visible


def test_an_edit_made_in_the_editor_is_noticed_on_return(gui):
    """The layout and the code are edited in different places, often together."""
    gui.toggle()
    _edit(gui, STARTUP_V2)
    gui.toggle()
    gui.root.update()
    assert gui.built.notice.visible


def test_a_broken_file_does_not_claim_startup_changed(gui):
    """Half-typed code is not an edited startup, and must not look like one."""
    _edit(gui, "def on_startup(ev):\n    ev.marker = (")
    _click(gui)
    assert not gui.built.notice.visible


# -- how the edit gets noticed at all ------------------------------------


def _no_handler_app(make_app):
    app = make_app()
    # An element with no handler written for it: the normal state of one just
    # drawn, and the case that used to go completely unreported.
    app.built.create_element("button", Rect(0.6, 0.1, 0.3, 0.2), tag="quiet")
    app.interface.code_path.write_text(STARTUP_V1, encoding="utf-8")
    app.toggle()
    return app


def test_clicking_an_element_with_no_handler_still_notices(make_app):
    """Reported as "nothing happens", and this was why.

    The check used to hang off the after-invoke hook, which only fires when a
    handler actually ran. Click an element you have not written code for - which
    is normal, and silent by design - and nothing looked at the file at all.
    """
    app = _no_handler_app(make_app)
    _edit(app, STARTUP_V2)
    app.built.handles["quiet"].widget.invoke()
    app.root.update()
    assert app.built.notice.visible


def test_saving_the_file_is_enough_on_its_own(gui):
    """No interaction at all. Saving is the moment something should happen."""
    import time

    _edit(gui, STARTUP_V2)
    deadline = time.time() + 5
    while time.time() < deadline and not gui.built.notice.visible:
        gui.root.update()
        time.sleep(0.05)
    assert gui.built.notice.visible, "the edit was never noticed without a click"


def test_an_untouched_file_is_never_declared_stale(gui):
    """The poll must not cry wolf while nobody is editing anything."""
    import time

    deadline = time.time() + 2
    while time.time() < deadline:
        gui.root.update()
        time.sleep(0.05)
    assert not gui.built.notice.visible


def test_the_poll_stops_when_the_mode_is_torn_down(gui):
    """A timer outliving its widgets fires into a destroyed frame."""
    runner = gui.built
    gui.toggle()
    assert runner._poll_id is None


# -- the top-bar button --------------------------------------------------


def _rerun_button(app):
    from tkinter import ttk

    buttons = [
        w for w in app.chrome.winfo_children()
        if isinstance(w, (app.tk.Button, ttk.Button))
        and "Re-run" in str(w.cget("text"))
    ]
    assert len(buttons) == 1, f"expected one re-run button, found {len(buttons)}"
    return buttons[0]


def test_the_top_bar_offers_re_running_startup(gui):
    _rerun_button(gui)  # raises if missing


def test_it_is_disabled_until_startup_is_actually_stale(gui):
    """The button is its own indicator: it comes alive when it would do something."""
    assert str(_rerun_button(gui).state()) != "()" or True
    assert "disabled" in _rerun_button(gui).state()

    _edit(gui, STARTUP_V2)
    gui.built.check_startup_staleness()
    gui.root.update()
    assert "disabled" not in _rerun_button(gui).state()


def test_pressing_the_top_bar_button_applies_the_edit(gui):
    _edit(gui, STARTUP_V2)
    gui.built.check_startup_staleness()
    _rerun_button(gui).invoke()
    gui.root.update()
    assert gui.built.ev.marker == "second"


def test_it_goes_quiet_again_once_startup_has_re_run(gui):
    _edit(gui, STARTUP_V2)
    gui.built.check_startup_staleness()
    _rerun_button(gui).invoke()
    gui.root.update()
    assert "disabled" in _rerun_button(gui).state()
    assert not gui.built.notice.visible


def test_it_is_disabled_in_the_editor(gui):
    """Nothing is running there, so there is nothing to re-run."""
    _edit(gui, STARTUP_V2)
    gui.built.check_startup_staleness()
    gui.toggle()
    assert "disabled" in _rerun_button(gui).state()
