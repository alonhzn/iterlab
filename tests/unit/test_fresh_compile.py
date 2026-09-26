"""The researcher's file is compiled from its source, never from a cache.

Found while checking the guide against the code. Its first worked example is
"change 2 to 5, save, and click" - and that edit, saved within a second of the
last load, did nothing. The loader noticed the change and reloaded, and Python
handed back the old compiled code from `__pycache__`, because it judges that
cache fresh by whole-second modification time and file size, and `2` and `5`
are the same size. No error, no fault banner: the old code simply ran.

A person rarely saves twice in one second. An editor that formats on save does
it routinely, and so does an assistant editing the file. The loader's whole job
is noticing edits, so it no longer defers to a cache that cannot see one.

No GUI.
"""

import sys
import traceback

import pytest

from iterlab.runtime.loader import ModuleLoader


@pytest.fixture
def clean_imports(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        sys.modules.pop(name, None)


def _click(loader):
    assert loader.refresh(), f"load failed: {loader.load_error}"
    return loader.resolve("on_clicked_go")(None)


# -- the defect ------------------------------------------------------------


def test_the_guides_own_example_takes_effect_immediately(tmp_path, clean_imports):
    """`2` to `5`, saved at once: same size, same second. It must run as `5`."""
    code = tmp_path / "demo.py"
    code.write_text("def on_clicked_go(ev):\n    return 2\n", encoding="utf-8")
    loader = ModuleLoader(code)
    assert _click(loader) == 2

    code.write_text("def on_clicked_go(ev):\n    return 5\n", encoding="utf-8")
    assert _click(loader) == 5


def test_many_same_size_edits_in_a_row(tmp_path, clean_imports):
    """Faster than any clock tick, and every one of them lands."""
    code = tmp_path / "demo.py"
    loader = ModuleLoader(code)
    for digit in range(10):
        code.write_text(f"def on_clicked_go(ev):\n    return {digit}\n", encoding="utf-8")
        assert _click(loader) == digit


def test_no_bytecode_is_left_beside_the_researcher_s_file(tmp_path, clean_imports):
    """Nothing to go stale, and no `__pycache__` clutter in their project."""
    code = tmp_path / "demo.py"
    code.write_text("def on_clicked_go(ev):\n    return 1\n", encoding="utf-8")
    _click(ModuleLoader(code))
    cache = tmp_path / "__pycache__"
    assert not cache.exists() or not list(cache.glob("demo.*.pyc"))


# -- and compiling it ourselves changes nothing else -----------------------


def test_iterlab_s_future_imports_do_not_leak_into_the_researcher_s_code(tmp_path, clean_imports):
    """The loader has `from __future__ import annotations`; their file does not.

    Inherited, it would silently turn every annotation in their code into a
    string. `dont_inherit=True` is what keeps their file behaving as Python
    would run it.
    """
    code = tmp_path / "demo.py"
    code.write_text(
        "def f(x: int):\n    pass\n\n\nEAGER = f.__annotations__['x'] is int\n",
        encoding="utf-8",
    )
    loader = ModuleLoader(code)
    assert loader.refresh(), loader.load_error
    assert loader.module.EAGER is True


def test_a_file_with_a_bom_and_non_ascii_text_loads(tmp_path, clean_imports):
    """Bytes are compiled, so an encoding marker is honoured as Python would."""
    code = tmp_path / "demo.py"
    code.write_bytes(
        "﻿LABEL = 'λ = 532 nm'\n\n\ndef on_clicked_go(ev):\n    return LABEL\n".encode("utf-8")
    )
    assert _click(ModuleLoader(code)) == "λ = 532 nm"


def test_a_fault_still_points_at_the_researcher_s_file_and_line(tmp_path, clean_imports):
    """The traceback a researcher reads must name their file, not `<string>`."""
    code = tmp_path / "demo.py"
    code.write_text("x = 1\ny = 2\nraise ValueError('line three')\n", encoding="utf-8")
    loader = ModuleLoader(code)
    assert loader.refresh() is False

    frames = traceback.extract_tb(loader.load_error.__traceback__)
    ours = [f for f in frames if f.filename == str(code)]
    assert ours, [f.filename for f in frames]
    assert ours[-1].lineno == 3


def test_a_helper_created_mid_session_is_found(tmp_path, clean_imports):
    """A brand new file, imported by an edit, on the very next click."""
    code = tmp_path / "demo.py"
    code.write_text("def on_clicked_go(ev):\n    return 'no helper yet'\n", encoding="utf-8")
    loader = ModuleLoader(code)
    assert _click(loader) == "no helper yet"

    name = "made_mid_session_helper"
    (tmp_path / f"{name}.py").write_text("VALUE = 'found it'\n", encoding="utf-8")
    code.write_text(
        f"import {name}\n\n\ndef on_clicked_go(ev):\n    return {name}.VALUE\n",
        encoding="utf-8",
    )
    assert _click(loader) == "found it"


def test_same_size_and_same_timestamp_is_still_a_change(tmp_path, clean_imports):
    """The collision a coarse file clock produces, made on purpose.

    Two saves inside one tick of the file clock - about 15 ms on Windows - stat
    identically. Waiting for that to happen by chance makes a test that fails
    two runs in five, so the timestamp is set back by hand instead: same size,
    same time to the nanosecond, different content. Only the digest can tell.
    """
    import os

    code = tmp_path / "demo.py"
    code.write_text("def on_clicked_go(ev):\n    return 2\n", encoding="utf-8")
    loader = ModuleLoader(code)
    assert _click(loader) == 2
    before = code.stat()

    code.write_text("def on_clicked_go(ev):\n    return 5\n", encoding="utf-8")
    os.utime(code, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert code.stat().st_mtime_ns == before.st_mtime_ns
    assert code.stat().st_size == before.st_size

    assert loader.has_changed(), "an edit the clock cannot see must still count"
    assert _click(loader) == 5
