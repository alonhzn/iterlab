"""Commit on Enter or focus loss, and the delete control.

There is no Apply button: a value typed and tabbed away from is a value the
researcher meant.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(mapped, make_app):
    app = make_app()
    d = app.built
    d.canvas.configure(width=400, height=400)
    app.root.update_idletasks()
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), name="go")
    d.select("go")
    app.root.update()
    return d


def _type(panel, field, value):
    """Type into a field the way a researcher does: focus it first.

    Key events are routed via the focus, so an unfocused entry never sees the
    Return.
    """
    entry = panel._entries[field]
    entry.focus_set()
    entry.update()
    entry.delete(0, "end")
    entry.insert(0, str(value))
    return entry


def test_there_is_no_apply_button(editor):
    texts = []

    def walk(widget):
        for child in widget.winfo_children():
            try:
                texts.append(str(child.cget("text")))
            except Exception:
                pass
            walk(child)

    walk(editor.properties.frame)
    assert not any("Apply" in t for t in texts), "the Apply button should be gone"


def test_enter_commits_the_edit(editor):
    entry = _type(editor.properties, "left", 0.5)
    entry.event_generate("<Return>")
    assert editor.layout.elements["go"].position.left == pytest.approx(0.5)


def test_losing_focus_commits_the_edit(editor):
    entry = _type(editor.properties, "width", 0.4)
    entry.event_generate("<FocusOut>")
    assert editor.layout.elements["go"].position.width == pytest.approx(0.4)


def test_committing_is_persisted(editor):
    from iterlab.layout import store

    entry = _type(editor.properties, "bottom", 0.6)
    entry.event_generate("<Return>")
    saved = store.load(editor.interface.layout_path)
    assert saved.elements["go"].position.bottom == pytest.approx(0.6)


def test_an_unchanged_field_does_not_rewrite_the_layout(editor):
    """Focus moves constantly; committing an unchanged value would churn the
    file and, worse, re-enter the rebuild that fires the next FocusOut."""
    before = editor.interface.layout_path.read_bytes()
    for field in ("left", "bottom", "width", "height"):
        editor.properties._entries[field].event_generate("<FocusOut>")
    assert editor.interface.layout_path.read_bytes() == before


def test_commit_on_focus_loss_does_not_recurse(editor):
    """Applying rebuilds the panel, destroying the focused entry, which makes
    Tk fire another FocusOut. Without a guard the two call each other."""
    entry = _type(editor.properties, "left", 0.45)
    entry.event_generate("<Return>")
    editor.app.root.update()
    assert editor.layout.elements["go"].position.left == pytest.approx(0.45)


def test_an_invalid_value_is_rejected_and_reported(editor):
    entry = _type(editor.properties, "left", "not a number")
    before = editor.layout.elements["go"].position
    entry.event_generate("<Return>")
    assert editor.layout.elements["go"].position == before
    assert editor.properties._message.cget("text") != ""


def test_enter_commits_a_rename(editor):
    entry = _type(editor.properties, "name", "fit_button")
    entry.event_generate("<Return>")
    assert "fit_button" in editor.layout.names()


# -- the delete control -----------------------------------------------------


def _delete_button(panel):
    from tkinter import ttk

    found = []

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, ttk.Button) and "Delete" in str(child.cget("text")):
                found.append(child)
            walk(child)

    walk(panel.frame)
    return found


def test_a_delete_control_exists_when_something_is_selected(editor):
    assert len(_delete_button(editor.properties)) == 1


def test_no_delete_control_when_nothing_is_selected(editor):
    editor.select(None)
    assert _delete_button(editor.properties) == []


def test_the_delete_control_removes_the_element(editor):
    _delete_button(editor.properties)[0].invoke()
    assert "go" not in editor.layout.names()
    assert editor.selected is None


def test_deleting_leaves_the_handler_in_the_code(editor):
    """Orphaned handlers are acceptable; destroyed work is not (FR-012)."""
    before = editor.interface.code_path.read_bytes()
    _delete_button(editor.properties)[0].invoke()
    assert editor.interface.code_path.read_bytes() == before
    assert b"on_clicked_go" in before
