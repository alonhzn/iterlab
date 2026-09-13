"""Style: the layout holds the starting appearance, code overrides it."""

import pytest

from iterlab.errors import LayoutInvalid
from iterlab.layout import store
from iterlab.layout.schema import (
    SCHEMA_VERSION,
    Element,
    Layout,
    Rect,
    Style,
    style_fields_for,
)


def test_a_plain_style_writes_nothing():
    """Defaults keep a minimal element terse (Principle II)."""
    assert Style().non_defaults() == {}


def test_only_non_defaults_are_recorded():
    assert Style(background="#ff0000", bold=True).non_defaults() == {
        "background": "#ff0000",
        "bold": True,
    }


@pytest.mark.parametrize("colour", ["#fff", "#ff5533", "red", "dark slate blue"])
def test_valid_colours_accepted(colour):
    assert Style(background=colour).background == colour


@pytest.mark.parametrize("colour", ["#gg0000", "#ff55", "", 42])
def test_invalid_colours_rejected(colour):
    with pytest.raises(ValueError):
        Style(background=colour)


def test_alignment_is_a_closed_set():
    with pytest.raises(ValueError):
        Style(align="sideways")


def test_font_size_is_bounded():
    with pytest.raises(ValueError):
        Style(font_size=0)
    with pytest.raises(ValueError):
        Style(font_size=500)


def test_edge_width_must_be_a_non_negative_whole_number():
    with pytest.raises(ValueError):
        Style(edge_width=-1)


def test_a_axes_has_only_visibility():
    """matplotlib owns how a plot looks; offering a fill colour would be a lie."""
    assert style_fields_for("axes") == ("visible",)


def test_text_types_carry_the_full_set():
    for element_type in ("button", "label"):
        available = style_fields_for(element_type)
        for field in ("background", "text_color", "edge", "edge_width",
                      "font", "font_size", "bold", "italic", "align",
                      "enabled", "visible"):
            assert field in available, f"{element_type} is missing {field}"


def test_restyle_rejects_a_property_the_type_does_not_have():
    layout = Layout()
    layout.add(Element("spectrum", "axes", Rect(0.1, 0.1, 0.4, 0.4)))
    with pytest.raises(ValueError):
        layout.restyle("spectrum", background="#ffffff")


# -- the file format --------------------------------------------------------


def _styled(tmp_path):
    layout = Layout()
    layout.add(Element("go", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go",
                       style=Style(background="#ff5533", bold=True, edge_width=2)))
    layout.add(Element("plain", "button", Rect(0.4, 0.1, 0.2, 0.1), label="Plain"))
    path = tmp_path / "demo.yaml"
    store.save(layout, path)
    return path, layout


def test_style_round_trips(tmp_path):
    path, layout = _styled(tmp_path)
    assert store.load(path).elements["go"].style == layout.elements["go"].style


def test_an_unstyled_element_gets_no_style_block(tmp_path):
    path, _ = _styled(tmp_path)
    text = path.read_text(encoding="utf-8")
    plain = text.split("plain:")[1]
    assert "style" not in plain, "a plain element should stay a three-line entry"


def test_unknown_style_key_is_rejected(tmp_path):
    path = tmp_path / "demo.yaml"
    path.write_text(
        f"schema_version: {SCHEMA_VERSION}\nelements:\n  go:\n    type: button\n"
        "    position: [0, 0, 0.1, 0.1]\n    style:\n      glow: true\n",
        encoding="utf-8",
    )
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_a_style_a_type_cannot_have_is_rejected(tmp_path):
    path = tmp_path / "demo.yaml"
    path.write_text(
        f"schema_version: {SCHEMA_VERSION}\nelements:\n  spectrum:\n    type: axes\n"
        "    position: [0, 0, 0.4, 0.4]\n    style:\n      bold: true\n",
        encoding="utf-8",
    )
    with pytest.raises(LayoutInvalid):
        store.load(path)


# -- migration --------------------------------------------------------------

V1_FILE = """schema_version: 1
window:
  width: 800
  height: 450
elements:
  run_fit:
    type: button
    position: [0.1, 0.1, 0.2, 0.1]
    label: Run fit
"""


def test_a_1x_yaml_layout_is_not_read(tmp_path):
    """2.0.0 changed the format and shipped no migration, on purpose.

    The library had no users, so nobody has a layout to lose - and a migration
    written for files that do not exist is a maintenance cost with no payer.
    What matters is that it fails as a file this build cannot read, rather than
    half-reading it.
    """
    path = tmp_path / "old.yaml"
    path.write_text(V1_FILE, encoding="utf-8")
    with pytest.raises(LayoutInvalid):
        store.load(path)


def test_the_old_file_is_left_exactly_as_it_was(tmp_path):
    """Refusing to read it must not be the same as damaging it."""
    path = tmp_path / "old.yaml"
    path.write_text(V1_FILE, encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(LayoutInvalid):
        store.load(path)
    assert path.read_bytes() == before


def test_opening_a_1x_project_says_what_happened(tmp_path, monkeypatch, capsys):
    """Otherwise it looks like opening a new interface and losing the old one."""
    from iterlab.app import _warn_about_a_1x_project
    from iterlab.interface import Interface

    (tmp_path / "demo.yaml").write_text(V1_FILE, encoding="utf-8")
    (tmp_path / "demo.py").write_text("def on_startup(ev):\n    pass\n", encoding="utf-8")

    interface = Interface(name="demo", directory=tmp_path)
    assert _warn_about_a_1x_project(interface) is True

    printed = capsys.readouterr().out
    assert "demo.yaml" in printed
    assert "1.x" in printed
    assert "has not been touched" in printed
    assert (tmp_path / "demo.yaml").read_text(encoding="utf-8") == V1_FILE


def test_nothing_is_said_when_there_is_no_old_file(tmp_path):
    from iterlab.app import _warn_about_a_1x_project
    from iterlab.interface import Interface

    assert _warn_about_a_1x_project(Interface(name="demo", directory=tmp_path)) is False
