"""Principle V: the researcher's code is sacred.

Layout edits must leave the `.py` byte-for-byte identical. Adding an element may
only append. Deleting one may not remove anything.
"""

import pytest

from iterlab.codegen import inject, templates
from iterlab.errors import CodeFileUnparseable
from iterlab.interface import Interface
from iterlab.layout.schema import Element, Rect

HAND_WRITTEN = '''"""Four hundred lines of real work, abbreviated."""

import numpy as np

CONSTANT = 3


def helper(x):
    """Not a handler at all."""
    return x * CONSTANT


def on_startup(ev):
    ev.data = np.arange(10)


def on_clicked_run_fit(ev, event):
    ev.result = helper(ev.data)
'''


def _interface(tmp_path, code=HAND_WRITTEN):
    interface = Interface("demo", tmp_path)
    interface.ensure_files()
    interface.code_path.write_text(code, encoding="utf-8")
    interface.load_layout()
    interface.layout.add(
        Element("run_fit", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Run fit")
    )
    interface.save_layout()
    return interface


def test_code_file_byte_identical_after_layout_edits(tmp_path):
    """Moving and resizing must not touch the code file at all (FR-014)."""
    interface = _interface(tmp_path)
    before = interface.code_path.read_bytes()

    interface.layout.move("run_fit", Rect(0.5, 0.5, 0.3, 0.2))
    interface.layout.relabel("run_fit", "Go")
    interface.save_layout()

    assert interface.code_path.read_bytes() == before


def test_adding_an_element_only_appends(tmp_path):
    interface = _interface(tmp_path)
    before = interface.code_path.read_text(encoding="utf-8")

    element = Element("spectrum", "plot_area", Rect(0.1, 0.4, 0.5, 0.4))
    interface.layout.add(element)
    inject.append_stub(interface.code_path, element, templates.default_stub(element))

    after = interface.code_path.read_text(encoding="utf-8")
    assert after.startswith(before), "existing content is a prefix — nothing was altered"
    assert "def on_clicked_spectrum" in after[len(before):]


def test_no_duplicate_after_reformat(tmp_path):
    """AST detection survives decorators, comments and odd formatting (FR-011)."""
    reformatted = (
        "import functools\n\n\n"
        "# a comment mentioning on_clicked_run_fit\n"
        "@functools.wraps(print)\n"
        "def on_clicked_run_fit(\n"
        "    ev,\n"
        "    event,\n"
        "):\n"
        "    pass\n"
    )
    interface = _interface(tmp_path, reformatted)
    element = interface.layout.elements["run_fit"]

    added = inject.append_stub(
        interface.code_path, element, templates.default_stub(element)
    )
    assert added is False
    assert interface.code_path.read_text(encoding="utf-8").count(
        "def on_clicked_run_fit"
    ) == 1


def test_delete_leaves_handler(tmp_path):
    """Orphaned handlers are acceptable; destroyed work is not (FR-012)."""
    interface = _interface(tmp_path)
    before = interface.code_path.read_bytes()

    interface.layout.remove("run_fit")
    interface.save_layout()

    assert "run_fit" not in interface.layout.tags()
    assert interface.code_path.read_bytes() == before
    assert "def on_clicked_run_fit" in interface.code_path.read_text(encoding="utf-8")


def test_unparseable_file_refuses_append(tmp_path):
    """Without an AST there is no way to know if the handler is already there.

    Appending blindly would risk a duplicate definition silently shadowing the
    researcher's own work (research.md R6).
    """
    interface = _interface(tmp_path, "def broken(\n")
    before = interface.code_path.read_bytes()
    element = interface.layout.elements["run_fit"]

    with pytest.raises(CodeFileUnparseable):
        inject.append_stub(interface.code_path, element, templates.default_stub(element))

    assert interface.code_path.read_bytes() == before, "nothing was written"


def test_nested_function_does_not_count_as_a_handler(tmp_path):
    """A handler must be at module level to be reachable by name."""
    source = (
        "def wrapper():\n"
        "    def on_clicked_run_fit(ev, event):\n"
        "        pass\n"
    )
    interface = _interface(tmp_path, source)
    element = interface.layout.elements["run_fit"]
    assert inject.append_stub(
        interface.code_path, element, templates.default_stub(element)
    ) is True


def test_windows_line_endings_are_preserved(tmp_path):
    """Adding an element must not reflow a Windows-authored file.

    `Path.read_text` normalizes CRLF to LF in memory; writing that back rewrites
    every line, so adding one stub would show up as a whole-file diff. That is
    a modification of lines the researcher wrote, which FR-014 forbids.
    """
    path = tmp_path / "demo.py"
    original = "def on_startup(ev):\r\n    pass\r\n"
    path.write_bytes(original.encode("utf-8"))

    element = Element("go", "button", Rect(0.1, 0.1, 0.2, 0.1))
    inject.append_stub(path, element, templates.default_stub(element))

    after = path.read_bytes()
    assert after.startswith(original.encode("utf-8")), "existing lines untouched"
    assert b"\r\n" in after.split(original.encode("utf-8"))[1], "stub matches the file"
    assert after.count(b"\n") == after.count(b"\r\n"), "no mixed line endings"


def test_unix_line_endings_stay_unix(tmp_path):
    path = tmp_path / "demo.py"
    original = "def on_startup(ev):\n    pass\n"
    path.write_bytes(original.encode("utf-8"))

    element = Element("go", "button", Rect(0.1, 0.1, 0.2, 0.1))
    inject.append_stub(path, element, templates.default_stub(element))

    after = path.read_bytes()
    assert after.startswith(original.encode("utf-8"))
    assert b"\r\n" not in after
