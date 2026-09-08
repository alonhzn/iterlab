"""Principle IV: reload discards nothing.

The paradigm's central economic claim. Expensive data loading happens once per
session, not once per edit.
"""

import time

from iterlab.runtime.dispatch import Dispatcher, Event
from iterlab.runtime.environment import Ev
from iterlab.runtime.faults import RecordingFaultSink
from iterlab.runtime.loader import CURRENT, ModuleLoader


def _write(path, text):
    # Filesystem mtime granularity is coarse on some systems, so nudge the clock
    # between writes rather than relying on it (research.md R2 caveat).
    time.sleep(0.01)
    path.write_text(text, encoding="utf-8")


def _session(tmp_path, source):
    path = tmp_path / "demo.py"
    path.write_text(source, encoding="utf-8")
    ev, sink = Ev(), RecordingFaultSink()
    return path, ev, sink, Dispatcher(ModuleLoader(path), ev, sink)


def _click(dispatcher, name="go"):
    return dispatcher.invoke(
        f"on_clicked_{name}", Event(kind="clicked", element=name, button="left")
    )


def test_env_survives_reload(tmp_path):
    """The object itself, not merely its contents, is the same after a reload."""
    path, ev, _, d = _session(
        tmp_path,
        "def on_startup(ev):\n    ev.data = list(range(1000))\n"
        "def on_clicked_go(ev, event):\n    ev.result = 1\n",
    )
    d.invoke("on_startup", args=(ev,))
    before = ev.data

    _write(path, "def on_startup(ev):\n    ev.data = []\n"
                 "def on_clicked_go(ev, event):\n    ev.result = 2\n")
    _click(d)

    assert ev.result == 2, "the edited handler ran"
    assert ev.data is before, "the researcher's data is the same object"
    assert len(ev.data) == 1000, "startup did not re-run and wipe it"


def test_unchanged_file_not_reloaded(tmp_path):
    """Repeated clicks between edits cost nothing (FR-026a)."""
    path, ev, _, d = _session(
        tmp_path,
        "COUNTER = []\n"
        "COUNTER.append(1)\n"  # module-level: re-runs on every actual reload
        "def on_clicked_go(ev, event):\n    ev.n = len(COUNTER)\n",
    )
    for _ in range(5):
        _click(d)
    assert ev.n == 1, "module top level executed once, not once per click"


def test_edit_is_picked_up_on_the_next_interaction(tmp_path):
    path, ev, _, d = _session(
        tmp_path, "def on_clicked_go(ev, event):\n    ev.v = 'first'\n"
    )
    _click(d)
    assert ev.v == "first"
    _write(path, "def on_clicked_go(ev, event):\n    ev.v = 'second'\n")
    _click(d)
    assert ev.v == "second", "no restart, no rebinding"


def test_new_handler_becomes_live_without_restart(tmp_path):
    """A handler added after launch works immediately (FR-025)."""
    path, ev, _, d = _session(tmp_path, "def on_startup(ev):\n    ev.ok = True\n")
    assert _click(d) is False, "nothing written for it yet"
    _write(path, "def on_startup(ev):\n    ev.ok = True\n"
                 "def on_clicked_go(ev, event):\n    ev.added = True\n")
    assert _click(d) is True
    assert ev.added is True


def test_startup_not_rerun_when_edited(tmp_path):
    """Editing startup does not re-invoke it (FR-026b, FR-026e)."""
    path, ev, _, d = _session(
        tmp_path,
        "def on_startup(ev):\n    ev.loaded = 'original'\n"
        "def on_clicked_go(ev, event):\n    ev.clicked = 1\n",
    )
    d.invoke("on_startup", args=(ev,))
    assert ev.loaded == "original"

    _write(path, "def on_startup(ev):\n    ev.loaded = 'edited'\n"
                 "def on_clicked_go(ev, event):\n    ev.clicked = 2\n")
    _click(d)

    assert ev.clicked == 2, "the handler is current"
    assert ev.loaded == "original", "startup was NOT re-run over a live session"


def test_failed_startup_retried_until_it_succeeds(tmp_path):
    """A typo in startup must not strand the session (FR-026d).

    This is the deferred *first* run, not a re-run: nothing was initialized, so
    nothing can be double-initialized.
    """
    path = tmp_path / "demo.py"
    path.write_text("def on_startup(ev)\n    ev.x = 1\n", encoding="utf-8")  # no colon
    ev, sink = Ev(), RecordingFaultSink()
    loader = ModuleLoader(path)

    state = {"done": False}

    def ensure_startup():
        if not state["done"] and d.invoke("on_startup", args=(ev,)):
            state["done"] = True

    d = Dispatcher(loader, ev, sink, before_invoke=ensure_startup)

    ensure_startup()
    assert state["done"] is False
    assert sink.kinds == ["load_failed"]

    _write(path, "def on_startup(ev):\n    ev.x = 42\n"
                 "def on_clicked_go(ev, event):\n    ev.clicked = True\n")
    _click(d)

    assert state["done"] is True, "startup ran on the next interaction"
    assert ev.x == 42
    assert ev.clicked is True


def test_loader_reports_state_transitions(tmp_path):
    path = tmp_path / "demo.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")
    loader = ModuleLoader(path)
    assert loader.refresh() is True
    assert loader.state == CURRENT

    _write(path, "def broken(\n")
    assert loader.refresh() is False
    assert loader.state == "broken"

    _write(path, "VALUE = 2\n")
    assert loader.refresh() is True, "broken is never terminal"
    assert loader.state == CURRENT
