"""A box reports a finished value, so a plot can follow what was entered.

Drawing a text or number box generates a handler, where it used to generate
nothing. It fires on a *committed* value rather than on every keystroke:
redrawing a plot per character is expensive and mostly meaningless, since "1" on
the way to "100" is a different plot drawn for nothing.

Two triggers, treated differently on purpose. Enter is deliberate, so it always
runs. Losing focus is incidental, so it runs only if the value actually moved.
"""

import pytest

from iterlab.layout.schema import DEFAULT_INTERACTION, Rect

from _helpers import keysym_for

pytestmark = pytest.mark.ui

COUNTER = "def on_changed_{tag}(ev, event):\n    ev.runs = getattr(ev, 'runs', 0) + 1\n"
RECORDER = "def on_changed_{tag}(ev, event):\n    ev.seen = ev.{tag}.{attr}\n"


@pytest.fixture
def editor(make_app):
    app = make_app()
    app.built.create_element("text_box", Rect(0.05, 0.6, 0.3, 0.1))
    app.built.create_element("number_box", Rect(0.05, 0.4, 0.2, 0.1))
    return app.built


# -- the stubs are generated -----------------------------------------------


def test_a_text_box_gets_a_changed_handler(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_changed_edt_0(ev, event):" in source


def test_a_number_box_gets_a_changed_handler(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "def on_changed_val_0(ev, event):" in source


def test_the_text_box_stub_prints_the_text(editor):
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "ev.edt_0.text" in source


def test_the_number_box_stub_prints_the_value_not_the_string(editor):
    """`.value` is what a researcher wants from a number box."""
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "ev.val_0.value" in source


def test_the_stub_says_it_is_not_per_keystroke(editor):
    """The one thing a reader would otherwise assume, given the old behaviour."""
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "Not on every keystroke" in source


def test_the_generated_file_still_parses(editor):
    compile(editor.interface.code_path.read_text(encoding="utf-8"), "demo.py", "exec")


def test_a_label_still_gets_nothing(editor):
    """It is written to, not interacted with."""
    editor.create_element("label", Rect(0.05, 0.2, 0.3, 0.1))
    source = editor.interface.code_path.read_text(encoding="utf-8")
    assert "on_changed_lbl_0" not in source
    assert "on_clicked_lbl_0" not in source


def test_the_declared_interaction_is_changed_for_both():
    assert DEFAULT_INTERACTION["text_box"] == "changed"
    assert DEFAULT_INTERACTION["number_box"] == "changed"


# -- and they fire on a committed value ------------------------------------


@pytest.fixture
def typing(mapped, make_app):
    """A GUI on a mapped root: Tk delivers synthesised events only to one."""
    app = make_app()
    app.built.create_element("text_box", Rect(0.05, 0.6, 0.3, 0.1))
    app.built.create_element("number_box", Rect(0.05, 0.4, 0.2, 0.1))
    app.toggle()
    return app


def _write(app, source):
    app.interface.code_path.write_text(source, encoding="utf-8")


def _type(app, tag, text, clear=False):
    """Type, without committing. Nothing here should reach a `changed` handler."""
    widget = app.built.handles[tag].widget
    widget.focus_set()
    app.root.update()
    if clear:
        widget.delete(0, "end")
    for character in str(text):
        widget.insert("end", character)
        widget.event_generate("<KeyRelease>", keysym=keysym_for(character), when="now")
    app.root.update()


def _commit(app, tag, how="<Return>"):
    widget = app.built.handles[tag].widget
    widget.update()
    widget.event_generate(how, when="now")
    widget.update()


def test_typing_alone_does_not_reach_the_handler(typing):
    """The whole point: a plot must not redraw once per character."""
    _write(typing, COUNTER.format(tag="edt_0"))
    _type(typing, "edt_0", "hello")
    assert getattr(typing.built.ev, "runs", 0) == 0


def test_enter_commits_it(typing):
    _write(typing, RECORDER.format(tag="edt_0", attr="text"))
    _type(typing, "edt_0", "spectrum.csv")
    _commit(typing, "edt_0")
    assert typing.built.ev.seen == "spectrum.csv"


def test_losing_focus_commits_it(typing):
    _write(typing, RECORDER.format(tag="edt_0", attr="text"))
    _type(typing, "edt_0", "abc")
    _commit(typing, "edt_0", how="<FocusOut>")
    assert typing.built.ev.seen == "abc"


def test_one_commit_per_edit_not_one_per_character(typing):
    _write(typing, COUNTER.format(tag="edt_0"))
    _type(typing, "edt_0", "abcdef")
    _commit(typing, "edt_0")
    assert typing.built.ev.runs == 1


def test_leaving_an_untouched_box_runs_nothing(typing):
    """Clicking past a box on the way somewhere else is not an edit."""
    _write(typing, COUNTER.format(tag="edt_0"))
    _commit(typing, "edt_0", how="<FocusOut>")
    _commit(typing, "edt_0", how="<FocusOut>")
    assert getattr(typing.built.ev, "runs", 0) == 0


def test_enter_runs_again_even_with_no_change(typing):
    """Enter is deliberate, so it is also how you re-run the same value."""
    _write(typing, COUNTER.format(tag="edt_0"))
    _type(typing, "edt_0", "x")
    _commit(typing, "edt_0")
    _commit(typing, "edt_0")
    assert typing.built.ev.runs == 2


def test_a_number_box_reports_a_number(typing):
    _write(typing, RECORDER.format(tag="val_0", attr="value"))
    _type(typing, "val_0", "12", clear=True)
    _commit(typing, "val_0")
    assert typing.built.ev.seen == 12


def test_an_emptied_number_box_reads_as_zero(typing):
    _write(typing, RECORDER.format(tag="val_0", attr="value"))
    _type(typing, "val_0", "", clear=True)
    _commit(typing, "val_0")
    assert typing.built.banner.visible is False
    assert typing.built.ev.seen == 0


def test_the_generated_stub_prints_on_commit(typing, capsys):
    """Through the real widget and the generated stub, not a hand-written one."""
    _type(typing, "edt_0", "ab")
    _commit(typing, "edt_0")
    assert "edt_0: ab" in capsys.readouterr().out


def test_per_keystroke_is_still_available_to_anyone_who_wants_it(typing):
    """`changed` is the new default, not a replacement for `key` (FR-017a)."""
    _write(typing, "def on_key_edt_0(ev, event):\n    ev.runs = getattr(ev, 'runs', 0) + 1\n")
    _type(typing, "edt_0", "abc")
    assert typing.built.ev.runs == 3


def test_this_is_what_lets_a_plot_follow_the_value(typing):
    """The case the handler exists for, end to end."""
    typing.toggle()
    typing.built.create_element("axes", Rect(0.4, 0.3, 0.55, 0.6))
    typing.toggle()
    _write(
        typing,
        "def on_changed_val_0(ev, event):\n"
        "    ev.ax_0.clear()\n"
        "    ev.ax_0.plot([0, 1, 2], [0, ev.val_0.value, 0])\n",
    )
    _type(typing, "val_0", "7", clear=True)
    _commit(typing, "val_0")
    assert typing.built.banner.visible is False
    assert len(typing.built.ev.ax_0.lines) == 1
