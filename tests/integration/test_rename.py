"""Renaming an element, and everything that refers to it.

This is the ONLY operation in iterlab permitted to modify a line the researcher
wrote (constitution Principle V). It reaches further than it used to - handlers,
attribute access, comments and strings - so the rule that keeps it safe carries
more weight: a name matches **whole or not at all**.

The case that decides the design: an interface holding `cmdRun` and
`cmdRunAlgorithm`. Renaming the first to `cmdRunData` must leave the second
completely alone. A text substitution turns it into `cmdRunDataAlgorithm` and
silently unwires an element the researcher never touched.

What is deliberately NOT renamed is a bare identifier that merely shares the
name. A local called `axes_0` is a coincidence; nothing here can tell it apart
from a reference, so it is left alone.
"""

import ast

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
    ev.axes_0.plot([1, 2, 3])


def on_clicked_axes_0(ev, event):
    axes_0 = 12          # a local that happens to share the name
    print(f"axes_0: {ev.axes_0.visible}", axes_0)
    return axes_0


def on_motion_axes_0(ev, event):
    pass


def on_clicked_axes_0_extra(ev, event):
    """A DIFFERENT element whose name merely starts with the old one."""
    ev.axes_0_extra.plot([1])


def helper_axes_0():
    return 1
'''


def _write(tmp_path, text=BEFORE):
    path = tmp_path / "demo.py"
    path.write_text(text, encoding="utf-8")
    return path


def _renamed(tmp_path, old="axes_0", new="spectrum", text=BEFORE):
    path = _write(tmp_path, text)
    result = rename.rename_tag(path, old, new)
    return path.read_text(encoding="utf-8"), result


# -- the handlers ----------------------------------------------------------


def test_every_handler_for_the_element_is_renamed(tmp_path):
    text, result = _renamed(tmp_path)
    assert "def on_clicked_spectrum(" in text
    assert "def on_motion_spectrum(" in text
    assert set(result.handlers) == {"on_clicked_axes_0", "on_motion_axes_0"}


def test_a_handler_for_another_element_is_not(tmp_path):
    """The case a text substitution gets wrong."""
    text, _ = _renamed(tmp_path)
    assert "def on_clicked_axes_0_extra(" in text
    assert "on_clicked_spectrum_extra" not in text


def test_a_function_that_is_not_a_handler_is_left_alone(tmp_path):
    text, _ = _renamed(tmp_path)
    assert "def helper_axes_0():" in text


# -- the references --------------------------------------------------------


def test_attribute_access_is_renamed(tmp_path):
    """`ev.axes_0` is the element, so it has to follow the element."""
    text, _ = _renamed(tmp_path)
    assert "ev.spectrum.plot([1, 2, 3])" in text
    assert "ev.axes_0.plot" not in text


def test_a_longer_attribute_is_not(tmp_path):
    """`ev.axes_0_cache` belongs to the researcher, not to the element."""
    text, _ = _renamed(tmp_path)
    assert "ev.axes_0_cache" in text


def test_another_elements_attribute_is_not(tmp_path):
    text, _ = _renamed(tmp_path)
    assert "ev.axes_0_extra.plot([1])" in text


def test_a_bare_local_is_left_alone(tmp_path):
    """A name that happens to match is not a reference to the element."""
    text, _ = _renamed(tmp_path)
    assert "    axes_0 = 12" in text
    assert "return axes_0" in text


# -- the mentions ----------------------------------------------------------


def test_comments_follow_the_rename(tmp_path):
    text, _ = _renamed(tmp_path)
    assert "# tuned against spectrum by hand" in text
    assert "# populate spectrum on launch" in text


def test_docstrings_follow_it_too(tmp_path):
    """Including the module docstring, which spans several lines."""
    text, _ = _renamed(tmp_path)
    assert "spectrum is the main plot." in text
    assert "axes_0 is the main plot." not in text


def test_strings_follow_it(tmp_path):
    text, _ = _renamed(tmp_path)
    assert 'ev.axes_0_cache = "spectrum"' in text


def test_an_f_string_follows_it_on_both_sides_of_the_brace(tmp_path):
    """The generated stub is exactly this shape, so both halves must move.

    The interpolation is code and would raise at runtime if it kept pointing at
    an element that no longer exists. The literal is a label and would lie.
    """
    text, _ = _renamed(tmp_path)
    assert 'f"spectrum: {ev.spectrum.visible}"' in text


def test_getattr_by_string_follows_it(tmp_path):
    source = 'def on_startup(ev):\n    print(getattr(ev, "axes_0"))\n'
    text, _ = _renamed(tmp_path, text=source)
    assert 'getattr(ev, "spectrum")' in text


# -- the case that decides the design --------------------------------------


CMDRUN = '''# cmdRun starts the run, cmdRunAlgorithm does the other thing


def on_clicked_cmdRun(ev, event):
    """Fires for cmdRun, not for cmdRunAlgorithm."""
    ev.lbl_0.text = f"cmdRun: {ev.cmdRun.text}"
    ev.cmdRun_cache = ev.cmdRunAlgorithm.text


def on_clicked_cmdRunAlgorithm(ev, event):
    pass
'''


@pytest.fixture
def cmdrun(tmp_path):
    path = _write(tmp_path, CMDRUN)
    rename.rename_tag(path, "cmdRun", "cmdRunData")
    return path.read_text(encoding="utf-8")


def test_the_other_element_is_untouched_everywhere(cmdrun):
    """Not in its handler, not in its attribute, not in prose."""
    assert "def on_clicked_cmdRunAlgorithm(" in cmdrun
    assert "ev.cmdRunAlgorithm.text" in cmdrun
    assert "cmdRunAlgorithm does the other thing" in cmdrun
    assert "not for cmdRunAlgorithm" in cmdrun
    assert "cmdRunDataAlgorithm" not in cmdrun, "a text substitution would do this"


def test_the_renamed_element_moved_everywhere(cmdrun):
    assert "def on_clicked_cmdRunData(" in cmdrun
    assert 'f"cmdRunData: {ev.cmdRunData.text}"' in cmdrun
    assert "# cmdRunData starts the run" in cmdrun
    assert "Fires for cmdRunData" in cmdrun


def test_a_longer_name_of_its_own_is_untouched(cmdrun):
    assert "ev.cmdRun_cache" in cmdrun


# -- and the file survives -------------------------------------------------


def test_the_line_count_never_changes(tmp_path):
    text, _ = _renamed(tmp_path)
    assert len(text.splitlines()) == len(BEFORE.splitlines())


def test_the_file_still_parses_afterwards(tmp_path):
    text, _ = _renamed(tmp_path)
    ast.parse(text)


def test_windows_line_endings_are_preserved(tmp_path):
    """A rename must not reflow the file."""
    path = tmp_path / "demo.py"
    source = "# note about axes_0\r\ndef on_clicked_axes_0(ev, event):\r\n    pass\r\n"
    path.write_bytes(source.encode("utf-8"))

    rename.rename_tag(path, "axes_0", "spectrum")

    after = path.read_bytes().decode("utf-8")
    assert after == (
        "# note about spectrum\r\ndef on_clicked_spectrum(ev, event):\r\n    pass\r\n"
    )


def test_refused_on_unparseable(tmp_path):
    """No parse means no way to tell a definition from a mention. Refuse."""
    broken = "def on_clicked_axes_0(ev, event)\n    pass\n"  # missing colon
    path = _write(tmp_path, broken)
    with pytest.raises(CodeFileUnparseable):
        rename.rename_tag(path, "axes_0", "spectrum")
    assert path.read_text(encoding="utf-8") == broken, "file must be unmodified"


def test_an_element_nobody_wrote_code_for_is_a_no_op(tmp_path):
    source = "def on_startup(ev):\n    pass\n"
    path = _write(tmp_path, source)
    assert not rename.rename_tag(path, "axes_0", "spectrum")
    assert path.read_text(encoding="utf-8") == source


def test_a_missing_code_file_is_not_an_error(tmp_path):
    assert not rename.rename_tag(tmp_path / "absent.py", "a", "b")


def test_renaming_to_the_same_name_changes_nothing(tmp_path):
    source = "def on_clicked_axes_0(ev, event):\n    pass\n"
    path = _write(tmp_path, source)
    assert not rename.rename_tag(path, "axes_0", "axes_0")
    assert path.read_text(encoding="utf-8") == source
