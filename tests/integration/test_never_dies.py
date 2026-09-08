"""Principle III: the process never dies because of the researcher's code.

And its equally important converse — "no handler written" must never look like
"your code is broken". Conflating those two is the defect that stopped the 2024
spike, and `test_missing_handler_is_silent` is the test that guards against it.
"""

import time

from iterlab.runtime.dispatch import Dispatcher, Event
from iterlab.runtime.environment import Ev
from iterlab.runtime.faults import HANDLER_RAISED, LOAD_FAILED, RecordingFaultSink
from iterlab.runtime.loader import ModuleLoader


def _session(tmp_path, source):
    path = tmp_path / "demo.py"
    path.write_text(source, encoding="utf-8")
    ev, sink = Ev(), RecordingFaultSink()
    return path, ev, sink, Dispatcher(ModuleLoader(path), ev, sink)


def _click(d, name="go"):
    return d.invoke(f"on_clicked_{name}", Event(kind="clicked", tag=name))


def _write(path, text):
    time.sleep(0.01)
    path.write_text(text, encoding="utf-8")


def test_syntax_error_reports_and_session_survives(tmp_path):
    _, _, sink, d = _session(tmp_path, "def on_clicked_go(ev, event)\n    pass\n")
    assert _click(d) is False
    assert sink.kinds == [LOAD_FAILED]
    assert "SyntaxError" in sink.faults[0].traceback_text


def test_failing_import_reports_and_session_survives(tmp_path):
    _, _, sink, d = _session(tmp_path, "import a_module_that_does_not_exist\n")
    assert _click(d) is False
    assert sink.kinds == [LOAD_FAILED]


def test_exception_at_module_level_reports_and_session_survives(tmp_path):
    _, _, sink, d = _session(tmp_path, "raise RuntimeError('boom at import')\n")
    assert _click(d) is False
    assert sink.kinds == [LOAD_FAILED]
    assert "boom at import" in sink.faults[0].traceback_text


def test_raising_handler_reports_with_traceback_and_survives(tmp_path):
    _, _, sink, d = _session(
        tmp_path, "def on_clicked_go(ev, event):\n    raise ValueError('nope')\n"
    )
    assert _click(d) is False
    assert sink.kinds == [HANDLER_RAISED]
    fault = sink.faults[0]
    assert fault.element == "go"
    assert "nope" in fault.message
    assert "on_clicked_go" in fault.traceback_text, "points into the researcher's code"


def test_missing_handler_is_silent(tmp_path):
    """The case that must NEVER be conflated with broken code.

    An element drawn before its behaviour is written is entirely normal. If this
    ever reports a fault, the tool has recreated the exact defect it was built
    to avoid.
    """
    _, _, sink, d = _session(tmp_path, "def on_startup(ev):\n    pass\n")
    assert _click(d) is False, "nothing ran"
    assert sink.faults == [], "and nothing at all was reported"


def test_missing_handler_and_broken_code_are_distinguishable(tmp_path):
    """Same outward result — nothing happened — but only one is reported."""
    quiet_dir, loud_dir = tmp_path / "a", tmp_path / "b"
    quiet_dir.mkdir()
    loud_dir.mkdir()
    _, _, quiet_sink, quiet = _session(quiet_dir, "def on_startup(ev):\n    pass\n")
    _, _, loud_sink, loud = _session(loud_dir, "def on_clicked_go(ev, event)\n    pass\n")

    assert _click(quiet) is False and quiet_sink.faults == []
    assert _click(loud) is False and loud_sink.kinds == [LOAD_FAILED]


def test_recovery_preserves_state(tmp_path):
    """Fix the typo and carry on — same session, same data (FR-031)."""
    path, ev, sink, d = _session(
        tmp_path,
        "def on_startup(ev):\n    ev.data = 'expensive'\n"
        "def on_clicked_go(ev, event):\n    ev.n = 1\n",
    )
    d.invoke("on_startup", args=(ev,))

    _write(path, "def on_clicked_go(ev, event)\n    ev.n = 2\n")  # typo
    assert _click(d) is False
    assert sink.kinds == [LOAD_FAILED]

    _write(path, "def on_clicked_go(ev, event):\n    ev.n = 3\n")  # fixed
    assert _click(d) is True
    assert ev.n == 3
    assert ev.data == "expensive", "nothing was lost across the fault"


def test_banner_cleared_once_corrected_code_runs(tmp_path):
    """Stale warnings must not accumulate (FR-033b)."""
    path, _, sink, d = _session(
        tmp_path, "def on_clicked_go(ev, event):\n    raise ValueError('x')\n"
    )
    _click(d)
    assert sink.cleared == []

    _write(path, "def on_clicked_go(ev, event):\n    ev.ok = True\n")
    _click(d)
    assert sink.cleared == ["go"], "the report was retracted"


def test_fault_at_launch_does_not_prevent_use(tmp_path):
    """FR-032: a broken file at launch still opens a usable session."""
    path, ev, sink, d = _session(tmp_path, "import nope_not_here\n")
    assert d.invoke("on_startup", args=(ev,)) is False
    assert sink.kinds == [LOAD_FAILED]

    _write(path, "def on_startup(ev):\n    ev.ready = True\n")
    assert d.invoke("on_startup", args=(ev,)) is True
    assert ev.ready is True


def test_keyboard_interrupt_is_not_swallowed(tmp_path):
    """Never crashing on *researcher* faults must not mean swallowing signals."""
    import pytest

    _, _, _, d = _session(
        tmp_path, "def on_clicked_go(ev, event):\n    raise KeyboardInterrupt\n"
    )
    with pytest.raises(KeyboardInterrupt):
        _click(d)
