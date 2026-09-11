"""Text boxes and number boxes, and the `.text` every element shares.

The boxes are where a researcher types a parameter, so the value they hold has
to be reachable the same way as every other element's - and the number box has
to refuse anything that is not a number without making it impossible to type a
negative or a decimal.
"""

import pytest

from iterlab.layout.schema import DEFAULT_TEXT, Rect
from _helpers import press_key

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    designer = app.built
    designer.create_element("button", Rect(0.05, 0.05, 0.2, 0.1))
    designer.create_element("label", Rect(0.05, 0.20, 0.2, 0.1))
    designer.create_element("text_box", Rect(0.05, 0.35, 0.3, 0.1))
    designer.create_element("number_box", Rect(0.05, 0.50, 0.2, 0.1))
    return designer


@pytest.fixture
def gui(editor):
    app = editor.app
    app.toggle()
    return app


# -- tags ------------------------------------------------------------------


def test_the_default_tags_use_the_short_prefixes(editor):
    assert set(editor.layout.tags()) == {"cmd_0", "lbl_0", "edt_0", "val_0"}


def test_the_prefixes_number_upward_per_type(editor):
    editor.create_element("text_box", Rect(0.5, 0.35, 0.3, 0.1))
    editor.create_element("button", Rect(0.5, 0.05, 0.2, 0.1))
    assert "edt_1" in editor.layout.tags()
    assert "cmd_1" in editor.layout.tags()


# -- default text ----------------------------------------------------------


def test_a_new_button_says_something_useful(editor):
    assert editor.layout.elements["cmd_0"].label == "Click here!"


def test_a_new_label_says_something_useful(editor):
    assert editor.layout.elements["lbl_0"].label == "Information:"


def test_a_new_text_box_is_empty(editor):
    """Anything else would be text the researcher has to delete first."""
    assert editor.layout.elements["edt_0"].label == ""


def test_a_new_number_box_holds_a_number(editor):
    """A number box with nothing in it is not in a valid state."""
    assert editor.layout.elements["val_0"].label == "0"


def test_the_defaults_are_declared_not_derived_from_the_tag():
    assert DEFAULT_TEXT["button"] == "Click here!"
    assert DEFAULT_TEXT["label"] == "Information:"


# -- one .text for every element -------------------------------------------


@pytest.mark.parametrize("tag", ["cmd_0", "lbl_0", "edt_0", "val_0"])
def test_every_text_element_reads_and_writes_dot_text(gui, tag):
    """The point of the shared name: no need to recall what kind of element it is."""
    handle = gui.built.ev._element_handles()[tag]
    handle.text = "hello"
    assert handle.text == "hello"


@pytest.mark.parametrize("tag", ["cmd_0", "lbl_0", "edt_0", "val_0"])
def test_label_is_an_alias_for_text_everywhere(gui, tag):
    handle = gui.built.ev._element_handles()[tag]
    handle.label = "aliased"
    assert handle.text == "aliased"


def test_a_box_shows_its_layout_text_on_screen(gui):
    box = gui.built.handles["val_0"]
    assert box.widget.get() == "0", "the widget, not just the handle"


def test_typing_into_a_box_is_visible_to_code(gui):
    """What a researcher does at the keyboard, read the way their code reads it."""
    box = gui.built.handles["edt_0"]
    box.widget.focus_set()
    box.widget.delete(0, "end")
    box.widget.insert(0, "spectrum.csv")
    gui.root.update()
    assert gui.built.ev.edt_0.text == "spectrum.csv"


# -- the number box --------------------------------------------------------


@pytest.mark.parametrize("typed", ["42", "-3", "0.25", "-0.5", "100.75"])
def test_a_number_box_accepts_numbers(gui, typed):
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    box.widget.insert(0, typed)
    gui.root.update()
    assert box.text == typed


@pytest.mark.parametrize("typed", ["abc", "1.2.3", "12x", "--5", "1-2"])
def test_a_number_box_refuses_what_is_not_a_number(gui, typed):
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    box.widget.insert(0, typed)
    gui.root.update()
    assert box.text != typed, f"{typed!r} should have been refused"


def test_a_decimal_point_can_be_typed(gui):
    """Rejecting "0." mid-keystroke makes a decimal impossible to enter."""
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    for character in "0.25":
        box.widget.insert("end", character)
    gui.root.update()
    assert box.text == "0.25"


def test_a_minus_sign_can_be_typed_first(gui):
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    for character in "-7":
        box.widget.insert("end", character)
    gui.root.update()
    assert box.text == "-7"


def test_value_gives_a_number_not_a_string(gui):
    box = gui.built.handles["val_0"]
    box.text = "12.5"
    assert box.value == 12.5
    assert isinstance(box.value, float)


def test_a_whole_number_comes_back_as_an_int(gui):
    """So `range(ev.val_0.value)` works without the researcher casting it."""
    box = gui.built.handles["val_0"]
    box.text = "8"
    assert box.value == 8
    assert isinstance(box.value, int)


def test_an_empty_box_reads_as_zero(gui):
    """Someone clearing the box to retype is mid-edit, not mistaken."""
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    gui.root.update()
    assert box.value == 0


def test_setting_value_shows_in_the_box(gui):
    box = gui.built.handles["val_0"]
    box.value = 3.5
    assert box.widget.get() == "3.5"


# -- style -----------------------------------------------------------------


@pytest.mark.parametrize("tag", ["edt_0", "val_0"])
def test_boxes_carry_the_full_style_set(gui, tag):
    """Same properties as a button or a label, in the editor and in code."""
    handle = gui.built.handles[tag]
    handle.background = "#fff3cd"
    handle.text_color = "#7a5300"
    handle.font_size = 14
    handle.bold = True
    assert handle.background == "#fff3cd"
    assert handle.text_color == "#7a5300"
    assert handle.font_size == 14
    assert handle.bold is True
    assert handle.widget.cget("bg") == "#fff3cd"


@pytest.mark.parametrize("tag", ["edt_0", "val_0"])
def test_a_box_can_be_hidden_and_disabled(gui, tag):
    handle = gui.built.handles[tag]
    handle.enabled = False
    assert str(handle.widget.cget("state")) == "disabled"
    handle.visible = False
    assert handle.widget.place_info() == {}


def test_the_editor_offers_the_text_of_a_box_as_a_basic_property(editor):
    editor.select("edt_0")
    assert "label" in editor.properties._entries, "the text field should be shown"


# -- handlers --------------------------------------------------------------


def test_a_box_gets_no_generated_stub(editor):
    """Its value is read inside another handler, not reacted to per keystroke."""
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "on_clicked_edt_0" not in source
    assert "on_clicked_val_0" not in source


@pytest.fixture
def typed_gui(mapped, make_app):
    """A GUI on a *mapped* root.

    Tk delivers a synthesised key event only to a viewable widget; on the
    withdrawn root the rest of these tests use, it is swallowed in silence.
    """
    app = make_app()
    app.built.create_element("text_box", Rect(0.05, 0.35, 0.3, 0.1))
    app.toggle()
    return app


def test_a_handler_written_by_hand_is_still_wired(typed_gui):
    """FR-017a: every interaction stays available on every element type."""
    typed_gui.interface.code_path.write_text(
        "def on_key_edt_0(ev, event):\n    ev.typed = ev.edt_0.text\n", encoding="utf-8"
    )
    box = typed_gui.built.handles["edt_0"]
    box.widget.focus_set()
    # Focus is granted on the next pass through the event loop; generating a key
    # event before that lands it nowhere.
    typed_gui.root.update()
    box.widget.insert(0, "x")
    press_key(box.widget, "x")
    typed_gui.root.update()
    assert getattr(typed_gui.built.ev, "typed", None) == "x"
