"""The editor's toolbar folds away, and the canvas keeps its pixels.

Both modes are now one size: the interface. The editor window is that plus the
toolbar, so the canvas is the very window the researcher will run in. Folding the
toolbar therefore has to change the *window*, not the canvas — otherwise tidying
the desk would quietly resize the interface.

Collapsed or not is kept in the layout, so it travels with the project.
"""

import pytest

from iterlab.layout.schema import Rect, Window
from iterlab.ui.app import SIDEBAR_ALLOWANCE, TOOLBAR_ALLOWANCE

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(mapped, make_app):
    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1), tag="go")
    app.root.update_idletasks()
    return app.built


def _canvas(designer):
    """Measure after Tk has actually applied the geometry.

    `update_idletasks` does not apply a window resize - only a full `update`
    does - so measuring too early catches the canvas mid-change, wider by the
    toolbar that has already gone.
    """
    designer.app.root.update()
    designer.app.root.update_idletasks()
    return designer.canvas.winfo_width(), designer.canvas.winfo_height()


# -- folding ---------------------------------------------------------------


def test_it_starts_expanded(editor):
    assert editor.collapsed is False
    assert editor.sidebar.outer.winfo_ismapped()
    assert not editor.strip.winfo_ismapped()


def test_collapsing_swaps_the_panel_for_the_strip(editor):
    editor.toggle_toolbar()
    editor.app.root.update_idletasks()
    assert editor.collapsed is True
    assert not editor.sidebar.outer.winfo_ismapped()
    assert editor.strip.winfo_ismapped()


def test_expanding_brings_it_back(editor):
    editor.toggle_toolbar()
    editor.toggle_toolbar()
    editor.app.root.update_idletasks()
    assert editor.collapsed is False
    assert editor.sidebar.outer.winfo_ismapped()


def test_the_strip_says_what_it_is(editor):
    """A bare chevron does not tell you what expanding would get you."""
    editor.toggle_toolbar()
    texts = []

    def walk(widget):
        try:
            texts.append(str(widget.cget("text")))
        except Exception:
            pass
        for child in widget.winfo_children():
            walk(child)

    walk(editor.strip)
    assert "Toolbar" in texts


def test_the_strip_is_narrower_than_the_panel(editor):
    assert TOOLBAR_ALLOWANCE < SIDEBAR_ALLOWANCE


# -- and the canvas does not move ------------------------------------------


def test_folding_keeps_the_canvas_the_same_size(editor):
    """The point: tidying the desk must not resize the interface."""
    before = _canvas(editor)
    editor.toggle_toolbar()
    assert _canvas(editor) == before


def test_folding_narrows_the_window_instead(editor):
    before = editor.app.root.winfo_width()
    editor.toggle_toolbar()
    editor.app.root.update()
    after = editor.app.root.winfo_width()
    assert after == before - (SIDEBAR_ALLOWANCE - TOOLBAR_ALLOWANCE)


def test_the_interface_size_is_unchanged_by_folding(editor):
    before = editor.interface.layout.window
    editor.toggle_toolbar()
    editor.toggle_toolbar()
    assert editor.interface.layout.window == before


def test_the_run_window_is_unaffected(editor):
    """Folding is an editor convenience; the interface never hears about it."""
    editor.toggle_toolbar()
    app = editor.app
    expected = app.interface.layout.window
    app.toggle()
    app.root.update_idletasks()
    assert (app.root.winfo_width(), app.root.winfo_height()) == (
        expected.width, expected.height
    )


# -- remembered with the project -------------------------------------------


def test_the_state_is_written_to_the_layout(editor):
    from iterlab.layout import store

    editor.toggle_toolbar()
    assert store.load(editor.interface.layout_path).toolbar_collapsed is True


def test_it_comes_back_collapsed(editor, make_app):
    editor.toggle_toolbar()
    editor.app.close()

    reopened = make_app()
    if reopened.mode != "editor":
        reopened.toggle()
    reopened.root.update_idletasks()
    assert reopened.built.collapsed is True
    assert reopened.built.strip.winfo_ismapped()


def test_a_collapsed_project_opens_at_the_right_width(editor, make_app):
    """The allowance follows the state, or the canvas would come back wrong."""
    editor.toggle_toolbar()
    window = editor.interface.layout.window
    editor.app.close()

    reopened = make_app()
    if reopened.mode != "editor":
        reopened.toggle()
    reopened.root.update_idletasks()
    assert reopened.root.winfo_width() == window.width + TOOLBAR_ALLOWANCE
    assert reopened.built.canvas.winfo_width() == window.width


# -- the controls are still reachable --------------------------------------


def test_the_palette_and_properties_survive_folding(editor):
    """Folded away, not destroyed: the panel is the same objects on return."""
    palette, properties = editor.palette, editor.properties
    editor.toggle_toolbar()
    editor.toggle_toolbar()
    assert editor.palette is palette
    assert editor.properties is properties


def test_selecting_while_folded_does_not_open_it(editor):
    """Nothing moves unless the researcher moves it."""
    editor.toggle_toolbar()
    editor.select("go")
    editor.app.root.update_idletasks()
    assert editor.collapsed is True


def test_an_element_can_still_be_selected_while_folded(editor):
    editor.toggle_toolbar()
    editor.select("go")
    assert editor.selected == "go"


def test_the_allowances_match_the_widths_they_stand_for():
    """The WYSIWYG guarantee rests on two numbers in two files agreeing.

    `app` adds an allowance to the interface size; `designer` packs a panel of
    some width beside the canvas. If they ever drift apart the canvas silently
    stops being the run window - which is the whole thing this is for, and it
    would go unnoticed because nothing would look broken.
    """
    from iterlab.ui.designer import SEPARATOR_WIDTH, SIDEBAR_WIDTH, TOOLBAR_WIDTH

    assert SIDEBAR_ALLOWANCE == SIDEBAR_WIDTH + SEPARATOR_WIDTH
    assert TOOLBAR_ALLOWANCE == TOOLBAR_WIDTH + SEPARATOR_WIDTH
