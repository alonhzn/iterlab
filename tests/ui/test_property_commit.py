"""A typed property is saved when focus leaves the field, whatever takes it.

Reported as: editing a property works if you tab to the next field, and is
silently lost if you click anything else — another element, the canvas, a
palette card.

`<FocusOut>` alone cannot carry this. Tk fires it when another *widget* takes
keyboard focus, and most of what a researcher clicks next does not take it: a
Canvas, an element drawn on it, a palette card are all unfocusable. Even when
focus does move, Tk delivers the event on the next pass through the event loop —
by which time the panel has been rebuilt for the new selection and the entry
holding the edit no longer exists.

So the events where focus really leaves commit explicitly and synchronously. The
one place that must *not* is `select`, which is the refresh path: a drag, a
resize and an apply all end there, and committing would write the panel's
now-stale text over the change that just happened.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.ui import dialogs

pytestmark = pytest.mark.ui


@pytest.fixture
def editor(make_app):
    app = make_app()
    designer = app.built
    designer.create_element("file_select", Rect(0.05, 0.60, 0.30, 0.10))
    designer.create_element("button", Rect(0.05, 0.30, 0.20, 0.10))
    designer.select("fileselect")
    return designer


def _type(panel, field, value):
    """Type into a field without committing, the way a person does."""
    if field not in ("tag", "label", "extensions") and not panel.advanced_open:
        panel.toggle_advanced()
    entry = panel._entries[field]
    entry.focus_set()
    entry.delete(0, "end")
    entry.insert(0, str(value))
    return entry


def _click(designer, tag):
    """Click an element on the canvas, which is how selection really changes."""
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements[tag].position)
    point = type("E", (), {"x": int((x0 + x1) / 2), "y": int((y0 + y1) / 2)})()
    designer._on_press(point)
    designer._on_release(point)


# -- the reported cases ----------------------------------------------------


def test_selecting_another_element_saves_the_edit(editor):
    _type(editor.properties, "extensions", "pdf")
    _click(editor, "cmd_0")
    assert editor.selected == "cmd_0"
    assert editor.layout.elements["fileselect"].extensions == "pdf"


def test_clicking_empty_canvas_saves_the_edit(editor):
    _type(editor.properties, "label", "Pick a PDF")
    blank = type("E", (), {"x": 700, "y": 430})()
    editor._on_press(blank)
    editor._on_release(blank)
    assert editor.layout.elements["fileselect"].label == "Pick a PDF"


def test_choosing_a_palette_type_saves_the_edit(editor):
    """Preparing to add a new element is "focus went elsewhere" too."""
    _type(editor.properties, "label", "Pick a PDF")
    editor.palette.selected.set("label")
    editor.app.root.update()
    assert editor.layout.elements["fileselect"].label == "Pick a PDF"


def test_opening_the_drawer_saves_the_edit(editor):
    """The More header is a Label, so it takes no focus of its own."""
    _type(editor.properties, "label", "Pick a PDF")
    editor.properties.toggle_advanced()
    assert editor.layout.elements["fileselect"].label == "Pick a PDF"


def test_a_geometry_edit_is_saved_the_same_way(editor):
    _type(editor.properties, "width", "0.4")
    _click(editor, "cmd_0")
    assert editor.layout.elements["fileselect"].position.width == pytest.approx(0.4)


def test_the_edit_reaches_the_file_on_disk(editor):
    """Not merely the layout in memory - a restart has to find it."""
    _type(editor.properties, "extensions", "pdf")
    _click(editor, "cmd_0")
    assert "pdf" in editor.interface.layout_path.read_text(encoding="utf-8")


# -- and the refresh path must NOT commit ----------------------------------


def test_dragging_an_element_is_not_undone_by_the_commit(editor):
    """The regression the first attempt at this fix caused.

    Committing inside `select` wrote the panel's stale position back over the
    drag that had just happened, and the element snapped home.
    """
    before = editor._to_pixels(editor.layout.elements["cmd_0"].position)
    start = type("E", (), {"x": int((before[0] + before[2]) / 2),
                           "y": int((before[1] + before[3]) / 2)})()
    editor._on_press(start)
    editor._on_drag(type("E", (), {"x": start.x + 60, "y": start.y + 40})())
    editor._on_release(type("E", (), {"x": start.x + 60, "y": start.y + 40})())

    after = editor._to_pixels(editor.layout.elements["cmd_0"].position)
    assert after[0] > before[0] + 20, "the element snapped back to where it started"


def test_committing_nothing_changes_nothing(editor):
    """Clicking about without typing must not rewrite the layout file."""
    before = editor.interface.layout_path.read_bytes()
    for _ in range(3):
        _click(editor, "cmd_0")
        _click(editor, "fileselect")
    assert editor.interface.layout_path.read_bytes() == before


# -- the bug this one was hiding -------------------------------------------


def test_an_extension_filter_typed_in_the_editor_reaches_the_chooser(editor, monkeypatch):
    """The originally reported symptom: typing pdf still offered every file.

    It was this same lost commit. The filter was never saved, so the chooser had
    nothing to filter by.
    """
    seen = {}
    monkeypatch.setattr(
        dialogs, "ask_open_file",
        lambda parent=None, initial_dir=None, extensions=(): seen.setdefault(
            "ext", extensions
        ) or "",
    )
    _type(editor.properties, "extensions", "pdf")
    _click(editor, "cmd_0")

    app = editor.app
    app.toggle()
    app.built.handles["fileselect"].widget.invoke()
    app.root.update()
    assert seen.get("ext") == ("pdf",)


def test_an_editor_change_to_extensions_beats_a_remembered_runtime_value(editor, monkeypatch):
    """The rule that already covered label and style, which extensions missed.

    Set from code, the value was kept across a mode switch — correctly — but it
    then beat an explicit edit in the editor, which it must not.
    """
    seen = {}
    monkeypatch.setattr(
        dialogs, "ask_open_file",
        lambda parent=None, initial_dir=None, extensions=(): seen.setdefault(
            "ext", extensions
        ) or "",
    )
    app = editor.app
    app.toggle()
    app.built.ev.fileselect.extensions = "csv"
    app.toggle()

    app.built.select("fileselect")
    _type(app.built.properties, "extensions", "pdf")
    _click(app.built, "cmd_0")

    app.toggle()
    app.built.handles["fileselect"].widget.invoke()
    app.root.update()
    assert seen.get("ext") == ("pdf",), "the editor edit lost to the runtime value"


def test_a_runtime_extension_still_survives_a_switch_when_nobody_edited_it(editor, monkeypatch):
    """The other half: preserving runtime state is still the default."""
    seen = {}
    monkeypatch.setattr(
        dialogs, "ask_open_file",
        lambda parent=None, initial_dir=None, extensions=(): seen.setdefault(
            "ext", extensions
        ) or "",
    )
    app = editor.app
    app.toggle()
    app.built.ev.fileselect.extensions = "csv"
    app.toggle()
    app.toggle()

    app.built.handles["fileselect"].widget.invoke()
    app.root.update()
    assert seen.get("ext") == ("csv",)
