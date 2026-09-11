"""An element with no text shows no text.

It used to fall back to its tag, so clearing a label's text produced a label
reading `lbl_0`. That made sense when a newly drawn element had no text at all
and would otherwise have been an invisible rectangle - but every type has a real
default now, so the fallback only ever fired when somebody had deliberately
cleared the text, which is the one moment it is certainly not what they meant.

The editor is the exception, and deliberately so: there you are working *on* the
elements, and one with nothing in it still has to be findable.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    designer = app.built
    designer.create_element("label", Rect(0.05, 0.70, 0.30, 0.10))
    designer.create_element("button", Rect(0.05, 0.50, 0.20, 0.10))
    designer.create_element("file_select", Rect(0.05, 0.30, 0.30, 0.10))
    return designer


def _clear(designer, tag):
    element = designer.layout.elements[tag]
    designer.apply_properties(tag, position=element.position, label="")


# -- the running interface -------------------------------------------------


@pytest.mark.parametrize("tag", ["lbl_0", "cmd_0", "fileselect"])
def test_an_empty_text_shows_nothing(editor, tag):
    _clear(editor, tag)
    app = editor.app
    app.toggle()
    assert app.built.ev._element_handles()[tag].text == ""


def test_a_label_cleared_in_the_editor_is_empty_in_the_interface(editor):
    """The reported case, through the editor rather than the model."""
    _clear(editor, "lbl_0")
    assert editor.layout.elements["lbl_0"].label == ""

    editor.app.toggle()
    assert editor.app.built.handles["lbl_0"].widget.cget("text") == ""


def test_clearing_it_from_code_leaves_it_empty(editor):
    app = editor.app
    app.toggle()
    app.built.ev.lbl_0.text = ""
    assert app.built.ev.lbl_0.text == ""
    assert app.built.handles["lbl_0"].widget.cget("text") == ""


def test_an_empty_text_stays_empty_across_a_mode_switch(editor):
    """Rebuilding must not quietly reintroduce the tag."""
    _clear(editor, "lbl_0")
    app = editor.app
    app.toggle()
    app.toggle()
    app.toggle()
    assert app.built.ev.lbl_0.text == ""


def test_an_empty_text_stays_empty_after_a_hard_reset(editor):
    _clear(editor, "lbl_0")
    app = editor.app
    app.toggle()
    app.restart_app()
    app.root.update()
    assert app.built.ev.lbl_0.text == ""


def test_text_set_back_to_something_still_shows(editor):
    """The fix must not turn into "never show text"."""
    _clear(editor, "lbl_0")
    app = editor.app
    app.toggle()
    app.built.ev.lbl_0.text = "loaded 42 rows"
    assert app.built.handles["lbl_0"].widget.cget("text") == "loaded 42 rows"


def test_the_defaults_are_untouched(make_app):
    """Nothing here changes what a *new* element says."""
    app = make_app()
    app.built.create_element("label", Rect(0.05, 0.7, 0.3, 0.1))
    app.built.create_element("button", Rect(0.05, 0.5, 0.2, 0.1))
    app.toggle()
    assert app.built.ev.lbl_0.text == "Information:"
    assert app.built.ev.cmd_0.text == "Click here!"


# -- the editor still labels what you are editing --------------------------


def test_the_editor_still_shows_the_tag_for_an_empty_element(editor):
    """Otherwise an emptied element is an unidentifiable rectangle to work on.

    The editor labels what you are editing; the interface shows what you wrote.
    """
    _clear(editor, "lbl_0")
    editor.redraw()
    editor.app.root.update_idletasks()

    texts = [
        editor.canvas.itemcget(item, "text")
        for item in editor.canvas.find_all()
        if editor.canvas.type(item) == "text"
    ]
    assert "lbl_0" in texts, f"the emptied element is unlabelled on the canvas: {texts}"


def test_the_editor_prefers_the_text_when_there_is_one(editor):
    editor.redraw()
    editor.app.root.update_idletasks()
    texts = [
        editor.canvas.itemcget(item, "text")
        for item in editor.canvas.find_all()
        if editor.canvas.type(item) == "text"
    ]
    assert "Information:" in texts
    assert "lbl_0" not in texts
