"""What the *running* interface changed must survive a mode switch.

The session already kept `ev` and the contents of a plot across a toggle. It did
not keep the widgets' own state, because a switch destroys every widget and
builds new ones from the layout file - so text somebody typed into a box, and a
colour or a caption a handler chose, silently reverted to whatever the file
said. Reported as "gui objects get reset when going to editor".

The rule is not "always put it back". An edit made in the editor is a decision,
and it has to beat a value the interface happened to be holding.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CODE = """
def on_startup(ev):
    ev.lbl_0.text = "set from code"
    ev.cmd_0.text = "Go"
"""


@pytest.fixture
def gui(make_app):
    app = make_app()
    designer = app.built
    designer.create_element("label", Rect(0.05, 0.70, 0.30, 0.10))
    designer.create_element("button", Rect(0.05, 0.50, 0.20, 0.10))
    designer.create_element("text_box", Rect(0.05, 0.30, 0.30, 0.10))
    designer.create_element("number_box", Rect(0.05, 0.10, 0.15, 0.10))
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    return app


def _round_trip(app):
    app.toggle()   # to the editor
    app.toggle()   # and back


# -- text ------------------------------------------------------------------


def test_text_typed_into_a_box_survives(gui):
    """The reported bug. Retyping a filename after nudging a button is absurd."""
    box = gui.built.handles["edt_0"]
    box.widget.insert(0, "spectrum.csv")
    gui.root.update()
    _round_trip(gui)
    assert gui.built.ev.edt_0.text == "spectrum.csv"


def test_a_number_typed_into_a_box_survives(gui):
    box = gui.built.handles["val_0"]
    box.widget.delete(0, "end")
    box.widget.insert(0, "42.5")
    gui.root.update()
    _round_trip(gui)
    assert gui.built.ev.val_0.value == 42.5


def test_a_label_set_from_code_survives(gui):
    """The other half of the report: a status line reverting to its default."""
    assert gui.built.ev.lbl_0.text == "set from code"
    _round_trip(gui)
    assert gui.built.ev.lbl_0.text == "set from code"


def test_a_button_caption_set_from_code_survives(gui):
    _round_trip(gui)
    assert gui.built.ev.cmd_0.text == "Go"


def test_text_set_after_startup_survives_too(gui):
    """Not only what startup did - anything the interface has done since."""
    gui.built.ev.lbl_0.text = "fitted in 2.1s"
    _round_trip(gui)
    assert gui.built.ev.lbl_0.text == "fitted in 2.1s"


# -- style -----------------------------------------------------------------


def test_a_colour_set_from_code_survives(gui):
    gui.built.ev.lbl_0.text_color = "#b00020"
    _round_trip(gui)
    assert gui.built.ev.lbl_0.text_color == "#b00020"
    assert gui.built.handles["lbl_0"].widget.cget("fg") == "#b00020"


def test_a_disabled_button_stays_disabled(gui):
    gui.built.ev.cmd_0.enabled = False
    _round_trip(gui)
    assert gui.built.ev.cmd_0.enabled is False
    assert str(gui.built.handles["cmd_0"].widget.cget("state")) == "disabled"


def test_a_hidden_element_stays_hidden(gui):
    gui.built.ev.lbl_0.visible = False
    _round_trip(gui)
    assert gui.built.ev.lbl_0.visible is False


# -- the editor still wins -------------------------------------------------


def test_editing_the_caption_in_the_editor_beats_the_remembered_one(gui):
    """An explicit edit is a decision; the old caption must not come back."""
    assert gui.built.ev.cmd_0.text == "Go"

    gui.toggle()
    element = gui.built.layout.elements["cmd_0"]
    gui.built.apply_properties("cmd_0", position=element.position, label="Run fit")
    gui.toggle()

    assert gui.built.ev.cmd_0.text == "Run fit", "the editor edit was overwritten"


def test_editing_the_style_in_the_editor_beats_the_remembered_one(gui):
    from dataclasses import replace

    gui.built.ev.lbl_0.text_color = "#b00020"

    gui.toggle()
    element = gui.built.layout.elements["lbl_0"]
    gui.built.layout.restyle("lbl_0", text_color="#1e7b34")
    gui.interface.save_layout()
    gui.toggle()

    assert gui.built.ev.lbl_0.text_color == "#1e7b34"


def test_moving_an_element_does_not_discard_its_text(gui):
    """Position is not presentation. Nudging a box must not empty it."""
    gui.built.handles["edt_0"].widget.insert(0, "keep me")
    gui.root.update()

    gui.toggle()
    element = gui.built.layout.elements["edt_0"]
    gui.built.apply_properties(
        "edt_0", position=Rect(0.40, 0.30, 0.30, 0.10), label=element.label
    )
    gui.toggle()

    assert gui.built.ev.edt_0.text == "keep me"


# -- restarting still clears ------------------------------------------------


def test_a_hard_reset_clears_it_all(gui):
    """Surviving a toggle is the point; surviving a restart would be a bug."""
    gui.built.handles["edt_0"].widget.insert(0, "typed")
    gui.built.ev.lbl_0.text_color = "#b00020"
    gui.root.update()

    gui.restart_app()
    gui.root.update()

    assert gui.built.ev.edt_0.text == ""
    assert gui.built.ev.lbl_0.text_color is None


def test_a_renamed_element_keeps_what_it_was_showing(gui):
    gui.built.handles["edt_0"].widget.insert(0, "keep me")
    gui.root.update()

    gui.toggle()
    element = gui.built.layout.elements["edt_0"]
    gui.built.apply_properties(
        "edt_0", tag="filename", position=element.position, label=element.label
    )
    gui.toggle()

    assert gui.built.ev.filename.text == "keep me"


def test_a_deleted_element_leaves_nothing_behind(gui):
    gui.built.handles["edt_0"].widget.insert(0, "typed")
    gui.root.update()
    gui.toggle()
    gui.built.select("edt_0")
    gui.built.delete_selected()
    gui.toggle()
    assert "edt_0" not in gui.built.session._presentation
