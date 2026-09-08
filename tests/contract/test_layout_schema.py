"""The layout file is public surface. These assert the contract, not the code."""

import pytest

from iterlab.errors import LayoutInvalid, LayoutVersionTooNew
from iterlab.layout import store
from iterlab.layout.schema import SCHEMA_VERSION, Element, Layout, Rect

MINIMAL = "schema_version: 1\nwindow:\n  width: 800\n  height: 450\nelements: {}\n"


def _sample():
    layout = Layout()
    layout.add(Element("spectrum", "plot_area", Rect(0.05, 0.30, 0.90, 0.65)))
    layout.add(Element("run_fit", "button", Rect(0.05, 0.10, 0.20, 0.10), label="Run fit"))
    return layout


def test_empty_layout_loads(tmp_path):
    p = tmp_path / "demo.yaml"
    p.write_text(MINIMAL, encoding="utf-8")
    layout = store.load(p)
    assert layout.is_empty
    assert layout.window.width == 800


def test_roundtrip_byte_identical(tmp_path):
    """Load then save with no edits must not change the file."""
    p = tmp_path / "demo.yaml"
    store.save(_sample(), p)
    first = p.read_bytes()
    store.save(store.load(p), p)
    assert p.read_bytes() == first


def test_element_order_preserved(tmp_path):
    p = tmp_path / "demo.yaml"
    store.save(_sample(), p)
    assert store.load(p).names() == ["spectrum", "run_fit"]


def test_version_is_always_written(tmp_path):
    p = tmp_path / "demo.yaml"
    store.save(Layout(), p)
    assert f"schema_version: {SCHEMA_VERSION}" in p.read_text(encoding="utf-8")


def test_newer_version_refused_and_file_untouched(tmp_path):
    """A newer file is reported and left exactly as it was.

    Opening it, dropping what this build does not understand, and saving it back
    would destroy the researcher's work invisibly.
    """
    p = tmp_path / "demo.yaml"
    original = "schema_version: 99\nwindow:\n  width: 640\nelements: {}\nfuture_key: kept\n"
    p.write_text(original, encoding="utf-8")
    before = p.read_bytes()

    with pytest.raises(LayoutVersionTooNew) as exc:
        store.load(p)

    assert exc.value.found == 99
    assert p.read_bytes() == before, "the file must not be modified"


def test_missing_version_is_invalid(tmp_path):
    p = tmp_path / "demo.yaml"
    p.write_text("window:\n  width: 800\nelements: {}\n", encoding="utf-8")
    with pytest.raises(LayoutInvalid):
        store.load(p)


def test_unknown_key_rejected_not_ignored(tmp_path):
    """Ignoring it would silently delete it on the next save."""
    p = tmp_path / "demo.yaml"
    p.write_text(MINIMAL.replace("elements: {}", "elements: {}\nmystery: 1"), encoding="utf-8")
    with pytest.raises(LayoutInvalid):
        store.load(p)


def test_unknown_element_key_rejected(tmp_path):
    p = tmp_path / "demo.yaml"
    p.write_text(
        "schema_version: 1\nelements:\n  a:\n    type: button\n"
        "    position: [0, 0, 0.1, 0.1]\n    colour: red\n",
        encoding="utf-8",
    )
    with pytest.raises(LayoutInvalid):
        store.load(p)


def test_invalid_element_name_in_file_rejected(tmp_path):
    p = tmp_path / "demo.yaml"
    p.write_text(
        "schema_version: 1\nelements:\n  class:\n    type: button\n"
        "    position: [0, 0, 0.1, 0.1]\n",
        encoding="utf-8",
    )
    with pytest.raises(LayoutInvalid):
        store.load(p)


def test_atomic_save_leaves_no_temp_files(tmp_path):
    store.save(_sample(), tmp_path / "demo.yaml")
    assert [p.name for p in tmp_path.iterdir()] == ["demo.yaml"]
