"""Atomic writes: an interruption must never truncate the researcher's file."""

import os

import pytest

from iterlab.codegen.templates import atomic_write

ORIGINAL = "def on_clicked_go(ev, event):\n    return 'precious'\n"


def test_original_survives_a_failed_write(tmp_path, monkeypatch):
    """The prior spike wrote through an open handle and could corrupt the file."""
    target = tmp_path / "demo.py"
    target.write_text(ORIGINAL, encoding="utf-8")

    real_replace = os.replace

    def explode(src, dst):
        raise OSError("interrupted at the worst possible moment")

    monkeypatch.setattr(os, "replace", explode)
    with pytest.raises(OSError):
        atomic_write(target, "replacement that must not land\n")
    monkeypatch.setattr(os, "replace", real_replace)

    assert target.read_text(encoding="utf-8") == ORIGINAL


def test_no_temp_file_left_behind_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "demo.py"
    target.write_text(ORIGINAL, encoding="utf-8")
    monkeypatch.setattr(os, "replace", lambda s, d: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        atomic_write(target, "nope\n")
    assert [p.name for p in tmp_path.iterdir()] == ["demo.py"]


def test_successful_write_replaces_content(tmp_path):
    target = tmp_path / "demo.py"
    target.write_text(ORIGINAL, encoding="utf-8")
    atomic_write(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"


def test_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "demo.py"
    atomic_write(target, "x\n")
    assert target.read_text(encoding="utf-8") == "x\n"
