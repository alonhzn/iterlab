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
    d.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    d.select("go")
    app.root.update()
    return d


#: Fields a researcher can reach without opening the "More" drawer.
BASIC_FIELDS = {"tag", "label"}


def _fire(entry, sequence):
    """Deliver an event to `entry` and let its handler finish.

    Two things, both needed. `when="now"` delivers immediately instead of
    queueing, and `update()` - not `update_idletasks()` - drains the queue
    afterwards, since only the former processes events. Without them an
    assertion on the next line races the handler it is meant to be testing.

    This is hygiene, not a workaround for a defect: the defect that made these
    tests flaky was a stale <FocusOut> committing into a rebuilt panel, and that
    is fixed in `properties.show`.
    """
    entry.update()
    entry.event_generate(sequence, when="now")
    entry.update()


def _type(panel, field, value):
    """Type into a field the way a researcher does: open it, then focus it.

    Key events are routed via the focus, and a widget inside a collapsed drawer
    is not on screen to receive them - so reaching a position or a colour means
    opening the drawer first, exactly as a person would have to.
    """
    if field not in BASIC_FIELDS and not panel.advanced_open:
        panel.toggle_advanced()
    panel.frame.update()
    entry = panel._entries[field]
    # Scroll it into view before focusing. In a short toolbar the field can be
    # below the fold, and Tk unmaps a canvas window that is scrolled out of
    # view - an unmapped widget takes no focus, so the keys would go nowhere.
    panel.reveal(entry)
    entry.update()
    entry.focus_force()
    entry.update()
    entry.delete(0, "end")
    entry.insert(0, str(value))
    entry.update_idletasks()
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
    _fire(entry, "<Return>")
    assert editor.layout.elements["go"].position.left == pytest.approx(0.5)


def test_losing_focus_commits_the_edit(editor):
    entry = _type(editor.properties, "width", 0.4)
    _fire(entry, "<FocusOut>")
    assert editor.layout.elements["go"].position.width == pytest.approx(0.4)


def test_committing_is_persisted(editor):
    from iterlab.layout import store

    entry = _type(editor.properties, "bottom", 0.6)
    _fire(entry, "<Return>")
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
    _fire(entry, "<Return>")
    editor.app.root.update()
    assert editor.layout.elements["go"].position.left == pytest.approx(0.45)


def test_an_invalid_value_is_rejected_and_reported(editor):
    entry = _type(editor.properties, "left", "not a number")
    before = editor.layout.elements["go"].position
    _fire(entry, "<Return>")
    assert editor.layout.elements["go"].position == before
    assert editor.properties._message.cget("text") != ""


def test_enter_commits_a_rename(editor):
    entry = _type(editor.properties, "tag", "fit_button")
    _fire(entry, "<Return>")
    assert "fit_button" in editor.layout.tags()


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
    assert "go" not in editor.layout.tags()
    assert editor.selected is None


def test_deleting_leaves_the_handler_in_the_code(editor):
    """Orphaned handlers are acceptable; destroyed work is not (FR-012)."""
    before = editor.interface.code_path.read_bytes()
    _delete_button(editor.properties)[0].invoke()
    assert editor.interface.code_path.read_bytes() == before
    assert b"on_clicked_go" in before


# -- in a window too short for the toolbar ---------------------------------


@pytest.fixture
def cramped(mapped, make_app):
    """An editor whose toolbar is taller than the room it has.

    Both modes are one window size now, so this is an ordinary state rather
    than an edge case: anyone working on a small interface is in it.
    """
    app = make_app()
    app.built.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    app.built.select("go")
    app.root.geometry("700x300")
    app.root.update()
    app.root.update_idletasks()
    return app.built


def test_the_toolbar_really_is_too_tall_here(cramped):
    """Guard on the fixture: without this the rest proves nothing."""
    sidebar = cramped.sidebar
    assert sidebar.inner.winfo_reqheight() > sidebar.canvas.winfo_height()


def test_a_field_below_the_fold_can_still_be_typed_into(cramped):
    """The failure this caused: typing into a field that went nowhere.

    Tk unmaps a canvas window scrolled out of view, and an unmapped widget
    cannot take focus - so the keys landed on nothing and the value was never
    committed. It failed on Linux only, where the toolbar runs taller.
    """
    _type(cramped.properties, "left", 0.5)
    _fire(cramped.properties._entries["left"], "<Return>")
    assert cramped.layout.elements["go"].position.left == pytest.approx(0.5)


def test_opening_the_drawer_brings_it_into_view(cramped):
    """Otherwise the drawer opens below the fold and appears to do nothing."""
    panel = cramped.properties
    assert panel.advanced_open is False
    panel.toggle_advanced()
    panel.frame.update_idletasks()

    drawer_top = panel._advanced.winfo_rooty() - panel.column.inner.winfo_rooty()
    showing = panel.column.canvas.canvasy(0)
    viewport = panel.column.canvas.winfo_height()
    assert showing <= drawer_top <= showing + viewport, (
        f"drawer at {drawer_top}, showing {showing} to {showing + viewport}"
    )


def test_revealing_does_nothing_when_everything_fits(mapped, make_app):
    """It must not jitter a column with no scrolling to do."""
    app = make_app()
    app.built.create_element("button", Rect(0.25, 0.25, 0.25, 0.25), tag="go")
    app.built.select("go")
    app.root.geometry("900x900")
    app.root.update()
    app.root.update_idletasks()

    column = app.built.sidebar
    before = column.canvas.yview()
    app.built.properties.reveal(app.built.properties._entries["tag"])
    assert column.canvas.yview() == before
