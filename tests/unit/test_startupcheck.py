"""Deciding whether `on_startup` has changed.

The judgement has to be narrow enough not to cry wolf on every handler edit and
wide enough to catch a change to a helper startup calls. Both halves matter: a
notice that appears on every save is one a researcher learns to ignore, and one
that misses a real change leaves them staring at code that never ran.
"""

import pytest

from iterlab.runtime.startupcheck import fingerprint

BASE = '''import numpy as np


def _load():
    return np.arange(10)


def on_startup(ev):
    ev.data = _load()


def on_clicked_go(ev, event):
    print("go")
'''


@pytest.fixture
def code(tmp_path):
    path = tmp_path / "demo.py"
    path.write_text(BASE, encoding="utf-8")
    return path


def test_an_unchanged_file_keeps_its_fingerprint(code):
    assert fingerprint(code) == fingerprint(code)


def test_editing_a_handler_does_not_claim_startup_changed(code):
    """The common case by far. A notice here would be pure noise."""
    before = fingerprint(code)
    code.write_text(BASE.replace('print("go")', 'print("went")'), encoding="utf-8")
    assert fingerprint(code) == before


def test_editing_startup_itself_is_noticed(code):
    before = fingerprint(code)
    code.write_text(BASE.replace("ev.data = _load()", "ev.data = _load() * 2"), encoding="utf-8")
    assert fingerprint(code) != before


def test_editing_a_helper_startup_calls_is_noticed(code):
    """Startup's behaviour is not confined to startup's own body."""
    before = fingerprint(code)
    code.write_text(BASE.replace("np.arange(10)", "np.arange(1000)"), encoding="utf-8")
    assert fingerprint(code) != before


def test_reformatting_is_not_a_change(code):
    """Compared as parsed structure, so comments and blank lines are free."""
    before = fingerprint(code)
    code.write_text(
        BASE.replace("def on_startup(ev):", "# load the data\ndef on_startup(ev):"),
        encoding="utf-8",
    )
    assert fingerprint(code) == before


def test_a_file_being_typed_into_raises_no_alarm(code):
    """Half-written code is not a changed startup; the next parse settles it."""
    code.write_text("def on_startup(ev):\n    ev.data = (", encoding="utf-8")
    assert fingerprint(code) is None


def test_a_file_with_no_startup_has_no_fingerprint(code):
    code.write_text("def on_clicked_go(ev, event):\n    pass\n", encoding="utf-8")
    assert fingerprint(code) is None


def test_indirect_helpers_are_followed(code):
    """Reachability is transitive, not one level deep."""
    code.write_text(
        "def _inner():\n    return 1\n"
        "def _outer():\n    return _inner()\n"
        "def on_startup(ev):\n    ev.v = _outer()\n",
        encoding="utf-8",
    )
    before = fingerprint(code)
    code.write_text(
        "def _inner():\n    return 2\n"
        "def _outer():\n    return _inner()\n"
        "def on_startup(ev):\n    ev.v = _outer()\n",
        encoding="utf-8",
    )
    assert fingerprint(code) != before


def test_recursion_does_not_hang(code):
    code.write_text(
        "def _f(n):\n    return 1 if n <= 0 else _f(n - 1)\n"
        "def on_startup(ev):\n    ev.v = _f(3)\n",
        encoding="utf-8",
    )
    assert fingerprint(code) is not None
