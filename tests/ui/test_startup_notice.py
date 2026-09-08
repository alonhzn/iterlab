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
