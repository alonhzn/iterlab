"""The layout file is public surface. These assert the contract, not the code.

2.0.0 replaced the YAML layout with `demo_layout.py`, a Python module holding
the layout *and* the class an editor reads to complete `ev.`. Two files instead
of three, and they cannot drift apart because one write produces both.

The rule that makes a Python layout safe is that iterlab never imports it. The
layout is lifted out of the parse tree and evaluated as literals, so opening
somebody else's interface stays as safe as opening a data file. That is the
first thing asserted here, because everything else is a detail beside it.
"""

import pytest

from iterlab.errors import LayoutInvalid, LayoutVersionTooNew
from iterlab.layout import store
from iterlab.layout.schema import SCHEMA_VERSION, Element, Layout, Rect

MINIMAL = (
    "LAYOUT = {'schema_version': %d, 'window': {'width': 800, 'height': 450}, "
    "'elements': {}}\n" % SCHEMA_VERSION
)


def _sample():
    layout = Layout()
    layout.add(Element("spectrum", "axes", Rect(0.05, 0.30, 0.90, 0.65)))
    layout.add(Element("run_fit", "button", Rect(0.05, 0.10, 0.20, 0.10), label="Run fit"))
    return layout


def _write(tmp_path, text, name="demo_layout.py"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# -- read, never run -------------------------------------------------------


def test_the_file_is_never_executed(tmp_path):
    """The guarantee the whole format rests on.

    A layout is something people send each other. If reading one ran it, every
    shared interface would be arbitrary code execution on open.
    """
    path = _write(
        tmp_path,
        "import pathlib\n"
        "pathlib.Path('evidence.txt').write_text('ran')\n"
        + MINIMAL,
    )
    store.load(path)
    assert not (tmp_path / "evidence.txt").exists(), "the file was executed"


def test_a_computed_value_is_refused_rather_than_evaluated(tmp_path):
    """Refusing is the honest answer: it is read without being run."""
    path = _write(tmp_path, "import os\nLAYOUT = {'schema_version': 8, 'pid': os.getpid()}\n")
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_a_file_with_no_layout_is_invalid(tmp_path):
    path = _write(tmp_path, "SOMETHING_ELSE = {}\n")
    with pytest.raises(LayoutInvalid) as exc:
        store.load(path)
    assert "LAYOUT" in str(exc.value)


def test_a_file_that_does_not_parse_is_invalid(tmp_path):
    path = _write(tmp_path, "LAYOUT = {'schema_version': 8,\n")
    with pytest.raises(LayoutInvalid):
        store.load(path)


# -- the shape of it -------------------------------------------------------


def test_empty_layout_loads(tmp_path):
    layout = store.load(_write(tmp_path, MINIMAL))
    assert layout.is_empty
    assert layout.window.width == 800


def test_roundtrip_byte_identical(tmp_path):
    """Load then save with no edits must not change the file."""
    path = tmp_path / "demo_layout.py"
    store.save(_sample(), path)
    first = path.read_bytes()
    store.save(store.load(path), path)
    assert path.read_bytes() == first


def test_element_order_preserved(tmp_path):
    path = tmp_path / "demo_layout.py"
    store.save(_sample(), path)
    assert store.load(path).tags() == ["spectrum", "run_fit"]


def test_what_is_written_is_valid_python(tmp_path):
    """It sits in the researcher's project. It cannot be a file that breaks."""
    import ast

    path = tmp_path / "demo_layout.py"
    store.save(_sample(), path)
    ast.parse(path.read_text(encoding="utf-8"))


def test_version_is_always_written(tmp_path):
    path = tmp_path / "demo_layout.py"
    store.save(Layout(), path)
    assert f"'schema_version': {SCHEMA_VERSION}" in path.read_text(encoding="utf-8")


def test_the_declarations_travel_with_the_layout(tmp_path):
    """One file, both jobs: what was drawn, and what an editor offers for it."""
    path = tmp_path / "demo_layout.py"
    store.save(_sample(), path)
    text = path.read_text(encoding="utf-8")
    assert 'spectrum: "Axes"' in text
    assert 'run_fit: "Button"' in text
    assert "from iterlab.types import Axes, Button" in text


# -- refusing what it cannot honour ----------------------------------------


def test_newer_version_refused_and_file_untouched(tmp_path):
    """A newer file is reported and left exactly as it was.

    Opening it, dropping what this build does not understand, and saving it back
    would destroy the researcher's work invisibly.
    """
    original = (
        "LAYOUT = {'schema_version': 99, 'window': {'width': 640}, "
        "'elements': {}, 'future_key': 'kept'}\n"
    )
    path = _write(tmp_path, original)
    before = path.read_bytes()

    with pytest.raises(LayoutVersionTooNew) as exc:
        store.load(path)

    assert exc.value.found == 99
    assert path.read_bytes() == before, "the file must not be modified"


def test_missing_version_is_invalid(tmp_path):
    path = _write(tmp_path, "LAYOUT = {'window': {'width': 800}, 'elements': {}}\n")
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_unknown_key_rejected_not_ignored(tmp_path):
    """Ignoring it would silently delete it on the next save."""
    path = _write(
        tmp_path,
        "LAYOUT = {'schema_version': %d, 'elements': {}, 'mystery': 1}\n" % SCHEMA_VERSION,
    )
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_unknown_element_key_rejected(tmp_path):
    path = _write(
        tmp_path,
        "LAYOUT = {'schema_version': %d, 'elements': {'a': {'type': 'button', "
        "'position': [0, 0, 0.1, 0.1], 'colour': 'red'}}}\n" % SCHEMA_VERSION,
    )
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_invalid_element_name_in_file_rejected(tmp_path):
    path = _write(
        tmp_path,
        "LAYOUT = {'schema_version': %d, 'elements': {'class': {'type': 'button', "
        "'position': [0, 0, 0.1, 0.1]}}}\n" % SCHEMA_VERSION,
    )
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_atomic_save_leaves_no_temp_files(tmp_path):
    store.save(_sample(), tmp_path / "demo_layout.py")
    assert [p.name for p in tmp_path.iterdir()] == ["demo_layout.py"]
