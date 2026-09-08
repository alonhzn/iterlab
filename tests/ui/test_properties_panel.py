"""The properties panel: typed values, labels, and renaming (FR-006, FR-005c-f)."""

import pytest

from iterlab.app import open_interface
from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    d = app.built
    d.create_element("button", Rect(0.05, 0.10, 0.25, 0.12), tag="run_fit")
    d.create_element("axes", Rect(0.05, 0.40, 0.90, 0.50), tag="spectrum")
    d.select("run_fit")
    yield app


def _set(panel, **values):
    for key, value in values.items():
        panel._entries[key].delete(0, "end")
        panel._entries[key].insert(0, str(value))
    return panel.apply()


def test_panel_shows_an_empty_state_when_nothing_is_selected(editor):
    editor.built.select(None)
    assert editor.built.properties.element_tag is None


def test_panel_exposes_the_contracted_properties(editor):
    from iterlab.layout.schema import style_fields_for

    d = editor.built
    core = {"tag", "left", "bottom", "width", "height"}

    assert set(d.properties._entries) == (
        core | {"label"} | set(style_fields_for("button"))
    )

    d.select("spectrum")
    assert set(d.properties._entries) == core | set(style_fields_for("axes")), (
        "a plot area has no text and no colours; matplotlib owns how it looks"
    )


def test_typed_coordinates_move_the_element(editor):
    """FR-006c: typing and dragging are one operation."""
    d = editor.built
    assert _set(d.properties, left=0.5, bottom=0.6, width=0.2, height=0.1) is True
    rect = editor.interface.layout.elements["run_fit"].position
    assert (rect.left, rect.bottom, rect.width, rect.height) == (0.5, 0.6, 0.2, 0.1)


def test_typed_change_is_persisted_immediately(editor):
    _set(editor.built.properties, left=0.3)
    text = editor.interface.layout_path.read_text(encoding="utf-8")
    assert "0.3" in text


def test_invalid_value_rejected_and_element_unchanged(editor):
    """FR-006e: the panel never accepts what it will discard."""
    d = editor.built
    before = editor.interface.layout.elements["run_fit"].position
    assert _set(d.properties, left="not a number") is False
    assert editor.interface.layout.elements["run_fit"].position == before
    assert d.properties._message.cget("text") != ""


def test_out_of_bounds_value_rejected(editor):
    d = editor.built
    before = editor.interface.layout.elements["run_fit"].position
    assert _set(d.properties, left=0.9, width=0.5) is False
    assert editor.interface.layout.elements["run_fit"].position == before


def test_editing_the_label_changes_nothing_else(editor):
    d = editor.built
    code_before = editor.interface.code_path.read_bytes()
    assert _set(d.properties, label="Run the fit") is True
    assert editor.interface.layout.elements["run_fit"].label == "Run the fit"
    assert editor.interface.layout.elements["run_fit"].tag == "run_fit"
    assert editor.interface.code_path.read_bytes() == code_before


def test_rename_rewrites_the_handler_and_nothing_else(editor):
    """FR-005d, and the reason rename is the sole exception to Principle V."""
    code = (
        "# a comment mentioning run_fit\n"
        "def on_startup(ev):\n"
        "    ev.note = 'run_fit'\n"
        "def on_clicked_run_fit(ev, event):\n"
        "    run_fit = 1\n"
        "    return run_fit\n"
    )
    editor.interface.code_path.write_text(code, encoding="utf-8")

    assert _set(editor.built.properties, tag="fit_button") is True

    after = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_clicked_fit_button(ev, event):" in after
    assert "# a comment mentioning run_fit" in after
    assert "ev.note = 'run_fit'" in after
    assert "    run_fit = 1" in after
    assert "fit_button" in editor.interface.layout.tags()


def test_rename_to_a_taken_name_is_refused(editor):
    d = editor.built
    code_before = editor.interface.code_path.read_bytes()
    assert _set(d.properties, tag="spectrum") is False
    assert "run_fit" in editor.interface.layout.tags()
    assert editor.interface.code_path.read_bytes() == code_before


def test_rename_to_a_keyword_is_refused(editor):
    assert _set(editor.built.properties, tag="class") is False
    assert "run_fit" in editor.interface.layout.tags()


def test_rename_refused_while_the_code_file_is_broken(editor):
    """FR-005f: both files are left exactly as they were."""
    broken = "def on_clicked_run_fit(ev, event)\n    pass\n"
    editor.interface.code_path.write_text(broken, encoding="utf-8")
    layout_before = editor.interface.layout_path.read_bytes()

    assert _set(editor.built.properties, tag="fit_button") is False

    assert editor.interface.code_path.read_text(encoding="utf-8") == broken
    assert editor.interface.layout_path.read_bytes() == layout_before
    assert "run_fit" in editor.interface.layout.tags()


def test_deleting_an_element_leaves_its_handler(editor):
    d = editor.built
    code_before = editor.interface.code_path.read_bytes()
    d.select("run_fit")
    d.delete_selected()
    assert "run_fit" not in editor.interface.layout.tags()
    assert editor.interface.code_path.read_bytes() == code_before
