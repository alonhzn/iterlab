"""A box reports every keystroke, so a plot can follow what is typed.

Drawing a text or number box now generates a handler, where it used to generate
nothing. The reason for the change is the case it makes possible: redrawing from
a value as someone types it, rather than after they click something else.
"""

import pytest

from iterlab.layout.schema import DEFAULT_INTERACTION, Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    app.built.create_element("text_box", Rect(0.05, 0.6, 0.3, 0.1))
    app.built.create_element("number_box", Rect(0.05, 0.4, 0.2, 0.1))
    return app.built


# -- the stubs are generated -----------------------------------------------


def test_a_text_box_gets_a_key_handler(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_key_edt_0(ev, event):" in source


def test_a_number_box_gets_a_key_handler(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_key_val_0(ev, event):" in source


def test_the_text_box_stub_prints_the_text(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "ev.edt_0.text" in source


def test_the_number_box_stub_prints_the_value_not_the_string(editor):
    """`.value` is what a researcher wants from a number box."""
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "ev.val_0.value" in source


def test_the_generated_file_still_parses(editor):
    compile(editor.interface.code_path.read_text(encoding="utf-8"), "demo.py", "exec")


def test_a_label_still_gets_nothing(editor):
    """It is written to, not interacted with."""
    editor.create_element("label", Rect(0.05, 0.2, 0.3, 0.1))
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "on_key_lbl_0" not in source
    assert "on_clicked_lbl_0" not in source


def test_the_declared_interaction_is_key_for_both():
    assert DEFAULT_INTERACTION["text_box"] == "key"
    assert DEFAULT_INTERACTION["number_box"] == "key"


# -- and they actually fire ------------------------------------------------


@pytest.fixture
def typing(mapped, make_app):
    """A GUI on a mapped root: Tk delivers synthesised keys only to one."""
    app = make_app()
    app.built.create_element("text_box", Rect(0.05, 0.6, 0.3, 0.1))
    app.built.create_element("number_box", Rect(0.05, 0.4, 0.2, 0.1))
    app.toggle()
    return app


def _type(app, tag, text):
    widget = app.built.handles[tag].widget
    widget.focus_set()
    app.root.update()
    for character in text:
        widget.insert("end", character)
        widget.event_generate("<KeyRelease>", keysym=character)
    app.root.update()


def test_typing_reaches_the_generated_handler(typing, capsys):
    """Through the real widget and the real stub, not a hand-written one."""
    _type(typing, "edt_0", "ab")
    printed = capsys.readouterr().out
    assert "edt_0: ab" in printed


def test_the_handler_sees_the_character_just_typed(typing):
    """Bound on release, so `.text` already holds it - not the previous value."""
    typing.interface.code_path.write_text(
        "def on_key_edt_0(ev, event):\n    ev.seen = ev.edt_0.text\n", encoding="utf-8"
    )
    _type(typing, "edt_0", "xy")
    assert typing.built.ev.seen == "xy"


def test_a_number_box_reports_a_number(typing):
    typing.interface.code_path.write_text(
        "def on_key_val_0(ev, event):\n    ev.seen = ev.val_0.value\n", encoding="utf-8"
    )
    typing.built.handles["val_0"].widget.delete(0, "end")
    _type(typing, "val_0", "12")
    assert typing.built.ev.seen == 12


def test_a_half_typed_number_does_not_raise(typing):
    """"-" on its way to "-5" must not fault the session mid-keystroke."""
    typing.interface.code_path.write_text(
        "def on_key_val_0(ev, event):\n    ev.seen = ev.val_0.value\n", encoding="utf-8"
    )
    typing.built.handles["val_0"].widget.delete(0, "end")
    _type(typing, "val_0", "-")
    assert typing.built.banner.visible is False
    assert typing.built.ev.seen == 0


def test_this_is_what_lets_a_plot_follow_the_typing(typing):
    """The case the change exists for, end to end."""
    typing.toggle()
    typing.built.create_element("axes", Rect(0.4, 0.3, 0.55, 0.6))
    typing.toggle()
    typing.interface.code_path.write_text(
        "def on_key_val_0(ev, event):\n"
        "    ev.ax_0.clear()\n"
        "    ev.ax_0.plot([0, 1, 2], [0, ev.val_0.value, 0])\n",
        encoding="utf-8",
    )
    typing.built.handles["val_0"].widget.delete(0, "end")
    _type(typing, "val_0", "7")
    assert typing.built.banner.visible is False
    assert len(typing.built.ev.ax_0.lines) == 1
