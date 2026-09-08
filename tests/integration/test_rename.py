"""Renaming an element's handlers.

This is the ONLY operation in iterlab permitted to modify a line the researcher
wrote (constitution Principle V). These tests are written before the
implementation on purpose: the obvious approach — substituting the old name as
text — passes the first two and fails `test_other_elements_untouched`.
"""

import pytest

from iterlab.codegen import rename
from iterlab.errors import CodeFileUnparseable

BEFORE = '''"""My analysis.

axes_0 is the main plot.
"""

import numpy as np

THRESHOLD = 0.5  # tuned against axes_0 by hand


def on_startup(ev):
    # populate axes_0 on launch
    ev.axes_0_cache = "axes_0"
    ev.spectrum.plot([1, 2, 3])


def on_clicked_axes_0(ev, event):
    axes_0 = 12          # a local that happens to share the name
    print("axes_0", axes_0)
    return axes_0


@staticmethod
def on_motion_axes_0(ev, event):
    pass


def on_clicked_axes_0_extra(ev, event):
    """A DIFFERENT element whose name merely starts with the old one."""
    pass


def helper_axes_0():
    return 1
'''


def _write(tmp_path, text=BEFORE):
    path = tmp_path / "demo.py"
    path.write_text(text, encoding="utf-8")
    return path


def test_all_handlers_for_element_renamed(tmp_path):
    path = _write(tmp_path)
    changed = rename.rename_handlers(path, "axes_0", "spectrum")
    text = path.read_text(encoding="utf-8")
    assert "def on_clicked_spectrum(" in text
    assert "def on_motion_spectrum(" in text
    assert set(changed) == {"on_clicked_axes_0", "on_motion_axes_0"}


def test_only_handler_names_change(tmp_path):
    """Comments, docstrings, strings, locals and formatting survive intact."""
    path = _write(tmp_path)
    before = BEFORE.splitlines()
    rename.rename_handlers(path, "axes_0", "spectrum")
    after = path.read_text(encoding="utf-8").splitlines()

    assert len(before) == len(after), "line count must not change"
    differing = [(b, a) for b, a in zip(before, after) if b != a]
    assert differing == [
        ("def on_clicked_axes_0(ev, event):", "def on_clicked_spectrum(ev, event):"),
        ("def on_motion_axes_0(ev, event):", "def on_motion_spectrum(ev, event):"),
    ]


def test_docstrings_and_comments_untouched(tmp_path):
    path = _write(tmp_path)
    rename.rename_handlers(path, "axes_0", "spectrum")
    text = path.read_text(encoding="utf-8")
    assert "axes_0 is the main plot." in text
    assert "# tuned against axes_0 by hand" in text
    assert "# populate axes_0 on launch" in text


def test_locals_and_string_literals_untouched(tmp_path):
    path = _write(tmp_path)
    rename.rename_handlers(path, "axes_0", "spectrum")
    text = path.read_text(encoding="utf-8")
    assert "    axes_0 = 12" in text
    assert 'print("axes_0", axes_0)' in text
    assert 'ev.axes_0_cache = "axes_0"' in text


def test_other_elements_untouched(tmp_path):
    """The case a text substitution gets wrong.

    `on_clicked_axes_0_extra` belongs to a DIFFERENT element whose name merely
    starts with the old one. Renaming it would silently unwire that element.
    """
    path = _write(tmp_path)
    rename.rename_handlers(path, "axes_0", "spectrum")
    text = path.read_text(encoding="utf-8")
    assert "def on_clicked_axes_0_extra(" in text
    assert "on_clicked_spectrum_extra" not in text


def test_non_handler_functions_untouched(tmp_path):
    path = _write(tmp_path)
    rename.rename_handlers(path, "axes_0", "spectrum")
    assert "def helper_axes_0():" in path.read_text(encoding="utf-8")


def test_refused_on_unparseable(tmp_path):
    """No AST means no way to tell a definition from a mention. Refuse."""
    broken = "def on_clicked_axes_0(ev, event)\n    pass\n"  # missing colon
    path = _write(tmp_path, broken)
    with pytest.raises(CodeFileUnparseable):
        rename.rename_handlers(path, "axes_0", "spectrum")
    assert path.read_text(encoding="utf-8") == broken, "file must be unmodified"


def test_element_with_no_handlers_succeeds(tmp_path):
    path = _write(tmp_path, "def on_startup(ev):\n    pass\n")
    assert rename.rename_handlers(path, "axes_0", "spectrum") == []
    assert path.read_text(encoding="utf-8") == "def on_startup(ev):\n    pass\n"


def test_missing_code_file_is_not_an_error(tmp_path):
    assert rename.rename_handlers(tmp_path / "absent.py", "a", "b") == []


def test_nested_function_not_treated_as_a_handler(tmp_path):
    """A handler must be at module level to be reachable by name."""
    source = (
        "def wrapper():\n"
        "    def on_clicked_axes_0(ev, event):\n"
        "        pass\n"
        "    return on_clicked_axes_0\n"
    )
    path = _write(tmp_path, source)
    assert rename.rename_handlers(path, "axes_0", "spectrum") == []
    assert path.read_text(encoding="utf-8") == source


def test_rename_preserves_windows_line_endings(tmp_path):
    """A rename must not reflow the file either."""
    path = tmp_path / "demo.py"
    source = "# note\r\ndef on_clicked_axes_0(ev, event):\r\n    pass\r\n"
    path.write_bytes(source.encode("utf-8"))

    rename.rename_handlers(path, "axes_0", "spectrum")

    after = path.read_bytes().decode("utf-8")
    assert after == "# note\r\ndef on_clicked_spectrum(ev, event):\r\n    pass\r\n"
