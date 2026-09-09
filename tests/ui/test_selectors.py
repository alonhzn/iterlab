"""File and folder selectors.

These are the first elements that open a modal dialog, and the suite refuses
modals outright (`tests/conftest.py`) because a suite that waits for a human is
not a release gate. So the dialog is replaced here, at the `ui.dialogs` seam —
never by patching `tkinter.filedialog`, which stays banned so that any path
reaching a real chooser fails loudly instead of hanging.
"""

import pytest

from iterlab.layout.schema import Rect, parse_extensions
from iterlab.runtime import remembered
from iterlab.ui import dialogs

pytestmark = pytest.mark.ui


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Never write to the real user state directory from a test."""
    monkeypatch.setattr(remembered, "state_dir", lambda: tmp_path / "state")


@pytest.fixture
def chooser(monkeypatch):
    """Stands in for the OS dialog, and records how it was called."""

    class Chooser:
        def __init__(self):
            self.answer = ""
            self.calls = []

        def _respond(self, **kwargs):
            self.calls.append(kwargs)
            return self.answer

    stub = Chooser()
    monkeypatch.setattr(
        dialogs, "ask_open_file",
        lambda parent=None, initial_dir=None, extensions=(): stub._respond(
            kind="file", initial_dir=initial_dir, extensions=extensions
        ),
    )
    monkeypatch.setattr(
        dialogs, "ask_directory",
        lambda parent=None, initial_dir=None: stub._respond(
            kind="folder", initial_dir=initial_dir
        ),
    )
    return stub


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("file_select", Rect(0.05, 0.6, 0.3, 0.1))
    app.built.create_element("folder_select", Rect(0.05, 0.4, 0.3, 0.1))
    app.built.create_element("label", Rect(0.05, 0.2, 0.5, 0.1))
    app.toggle()
    return app


def _pick(gui, tag, chooser, answer):
    chooser.answer = str(answer)
    gui.built.handles[tag].widget.invoke()
    gui.root.update()


# -- tags and captions -----------------------------------------------------


def test_the_first_of_each_takes_the_bare_tag(gui):
    """`fileselect`, not `fileselect_0` - there is almost always only one."""
    tags = gui.interface.layout.tags()
    assert "fileselect" in tags
    assert "folderselect" in tags


def test_a_second_one_is_numbered_from_one(gui):
    gui.toggle()
    gui.built.create_element("file_select", Rect(0.5, 0.6, 0.3, 0.1))
    assert "fileselect_1" in gui.interface.layout.tags()


def test_the_captions_say_what_the_buttons_do(gui):
    assert gui.built.ev.fileselect.text == "Select a File"
    assert gui.built.ev.folderselect.text == "Select a Folder"


def test_the_caption_does_not_change_when_something_is_chosen(gui, chooser, tmp_path):
    """Deliberate: the caption is the researcher's to control, not ours."""
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)
    assert gui.built.ev.fileselect.text == "Select a File"


# -- choosing --------------------------------------------------------------


def test_clicking_opens_the_chooser(gui, chooser):
    gui.built.handles["fileselect"].widget.invoke()
    gui.root.update()
    assert [c["kind"] for c in chooser.calls] == ["file"]


def test_the_folder_button_opens_the_folder_chooser(gui, chooser):
    gui.built.handles["folderselect"].widget.invoke()
    gui.root.update()
    assert [c["kind"] for c in chooser.calls] == ["folder"]


def test_a_chosen_file_lands_on_dot_path(gui, chooser, tmp_path):
    target = tmp_path / "spectrum.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)
    assert gui.built.ev.fileselect.path == str(target)


def test_a_chosen_folder_lands_on_dot_path(gui, chooser, tmp_path):
    _pick(gui, "folderselect", chooser, tmp_path)
    assert gui.built.ev.folderselect.path == str(tmp_path)


def test_nothing_is_chosen_to_begin_with(gui):
    assert gui.built.ev.fileselect.path == ""
    assert gui.built.ev.folderselect.path == ""


def test_cancelling_changes_nothing(gui, chooser, tmp_path):
    target = tmp_path / "keep.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)

    _pick(gui, "fileselect", chooser, "")   # cancelled
    assert gui.built.ev.fileselect.path == str(target), "a cancel discarded the choice"


def test_the_handler_runs_after_the_choice_not_before(gui, chooser, tmp_path):
    """So `ev.fileselect.path` is already set when the researcher's code reads it."""
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    gui.interface.code_path.write_text(
        "def on_clicked_fileselect(ev, event):\n"
        "    ev.seen = ev.fileselect.path\n"
        "    ev.from_event = event.path\n",
        encoding="utf-8",
    )
    _pick(gui, "fileselect", chooser, target)
    assert gui.built.ev.seen == str(target)
    assert gui.built.ev.from_event == str(target)


def test_cancelling_does_not_call_the_handler(gui, chooser):
    gui.interface.code_path.write_text(
        "def on_clicked_fileselect(ev, event):\n    ev.ran = True\n", encoding="utf-8"
    )
    _pick(gui, "fileselect", chooser, "")
    assert getattr(gui.built.ev, "ran", None) is None


# -- extensions ------------------------------------------------------------


def test_the_extension_filter_reaches_the_chooser(gui, chooser):
    gui.built.ev.fileselect.extensions = "txt, csv"
    gui.built.handles["fileselect"].widget.invoke()
    gui.root.update()
    assert chooser.calls[-1]["extensions"] == ("txt", "csv")


def test_no_filter_means_every_file(gui, chooser):
    gui.built.handles["fileselect"].widget.invoke()
    gui.root.update()
    assert chooser.calls[-1]["extensions"] == ()


def test_the_filter_is_stored_in_the_layout(gui):
    gui.toggle()
    element = gui.built.layout.elements["fileselect"]
    gui.built.apply_properties(
        "fileselect", position=element.position, label=element.label,
        extensions="txt, csv",
    )
    assert gui.interface.layout.elements["fileselect"].extensions == "txt, csv"
    assert "extensions" in gui.interface.layout_path.read_text(encoding="utf-8")


def test_a_folder_selector_has_no_extension_filter():
    from iterlab.layout.schema import Element

    with pytest.raises(ValueError, match="extension"):
        Element("folderselect", "folder_select", Rect(0, 0, 0.1, 0.1), extensions="csv")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("txt, jpeg, png, csv", ("txt", "jpeg", "png", "csv")),
        (".TXT , *.csv", ("txt", "csv")),
        ("", ()),
    ],
)
def test_extensions_are_parsed_forgivingly(raw, expected):
    assert parse_extensions(raw) == expected


def test_the_chooser_always_offers_all_files_as_well():
    """A filter nobody can escape is a trap when one file has the wrong suffix."""
    types = dialogs.filetypes_for(("csv",))
    assert types[-1] == ("All files", "*.*")
    assert "*.csv" in types[0][1]


# -- remembering -----------------------------------------------------------


def test_the_choice_survives_a_mode_switch(gui, chooser, tmp_path):
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)

    gui.toggle()
    gui.toggle()
    assert gui.built.ev.fileselect.path == str(target)


def test_the_choice_survives_a_hard_reset(gui, chooser, tmp_path):
    """A hard reset empties `ev`, but this lives on disk, not in the session."""
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)

    gui.restart_app()
    gui.root.update()
    assert gui.built.ev.fileselect.path == str(target)


def test_the_choice_survives_the_process(gui, chooser, tmp_path, make_app):
    """The point of storing it on disk: a new process finds it again."""
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)
    gui.close()

    reopened = make_app()
    if reopened.mode != "gui":
        reopened.toggle()
    assert reopened.built.ev.fileselect.path == str(target)


def test_a_deleted_file_reads_as_nothing_chosen(gui, chooser, tmp_path):
    """`if ev.fileselect.path:` must not pass for a file that has gone."""
    target = tmp_path / "temporary.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)
    assert gui.built.ev.fileselect.path == str(target)

    target.unlink()
    assert gui.built.ev.fileselect.path == ""


def test_the_chooser_reopens_where_the_last_choice_was(gui, chooser, tmp_path):
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)

    gui.built.handles["fileselect"].widget.invoke()
    gui.root.update()
    assert chooser.calls[-1]["initial_dir"] == str(target)


def test_a_deleted_file_still_offers_its_folder(gui, chooser, tmp_path):
    target = tmp_path / "renamed.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)
    target.unlink()

    gui.built.handles["fileselect"].widget.invoke()
    gui.root.update()
    assert chooser.calls[-1]["initial_dir"] == str(tmp_path)


def test_nothing_is_written_into_the_project_folder(gui, chooser, tmp_path):
    """The interface stays the two files it has always been."""
    # Somewhere other than the interface's own folder, or the file being chosen
    # would itself be what the assertion trips over.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target = elsewhere / "data.csv"
    target.write_text("x", encoding="utf-8")
    _pick(gui, "fileselect", chooser, target)

    names = sorted(p.name for p in gui.interface.dir.iterdir() if p.is_file())
    assert names == ["demo.py", "demo.yaml"], names


# -- it is a button in every other respect ---------------------------------


def test_a_selector_carries_the_full_style_set(gui):
    handle = gui.built.handles["fileselect"]
    handle.background = "#e6f0ea"
    handle.bold = True
    assert handle.background == "#e6f0ea"
    assert handle.widget.cget("bg") == "#e6f0ea"


def test_the_generated_stub_shows_how_to_read_the_path(gui):
    """Where a researcher actually finds out the attribute is called `.path`."""
    source = gui.interface.code_path.read_text(encoding="utf-8")
    assert "def on_clicked_fileselect(ev, event):" in source
    assert "ev.lbl_0.text = ev.fileselect.path" in source
    assert "def on_clicked_folderselect(ev, event):" in source
