"""Right-click an element in the editor to go to its handlers.

The menu is never posted here: on Windows, posting a Tk popup runs a loop of
its own until the menu closes, which would hang the suite. The designer posts
through `_post_menu`, which these replace; the menu itself is read and invoked
entry by entry, which is exactly what a click on an entry does.

No editor is ever started either. `editors.open_at` is replaced by a recorder,
and every test runs against a private state directory, so a choice made here
never reaches the real remembered one.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.runtime import editors, remembered
from iterlab.ui import handler_menu

pytestmark = pytest.mark.ui

CODE = '''def on_startup(ev):
    pass


def on_clicked_go(ev, event):
    print("go")
'''


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(remembered, "state_dir", lambda: tmp_path / "state")


@pytest.fixture
def detected(monkeypatch):
    """What detection finds; None by default so a test says what it assumes."""
    found = {"id": None}
    monkeypatch.setattr(editors, "detect", lambda environ=None, parents=None: found["id"])
    monkeypatch.setattr(
        editors, "available",
        lambda parents=None: {e.id: (None if e.id == "sublime" else "L") for e in editors.EDITORS},
    )
    return found


@pytest.fixture
def opened(monkeypatch):
    calls = []

    def record(editor_id, path, line, parents=None, popen=None):
        calls.append((editor_id, path.name, line))

    monkeypatch.setattr(editors, "open_at", record)
    return calls


@pytest.fixture
def designer(mapped, make_app, detected, opened):
    app = make_app()
    d = app.built
    d.canvas.configure(width=400, height=400)
    d._size = lambda: (400, 400)
    app.root.update()
    d.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    d.create_element("text_box", Rect(0.5, 0.5, 0.3, 0.1), tag="edt")
    d.create_element("label", Rect(0.1, 0.7, 0.3, 0.1), tag="status")
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    d.select(None)
    return d


def _centre(designer, tag):
    x0, y0, x1, y1 = designer._to_pixels(designer.layout.elements[tag].position)
    return int((x0 + x1) / 2), int((y0 + y1) / 2)


def _right_click(designer, point):
    posted = []
    designer._post_menu = lambda menu, x, y: posted.append(menu)
    designer.canvas.event_generate("<Button-3>", x=point[0], y=point[1])
    designer.app.root.update()
    return posted


def _labels(menu):
    out = []
    for index in range(menu.index("end") + 1):
        kind = menu.type(index)
        if kind == "separator":
            out.append("---")
        else:
            accelerator = menu.entrycget(index, "accelerator") if kind == "command" else ""
            out.append((menu.entrycget(index, "label"), accelerator))
    return out


def _index(menu, label):
    for index in range(menu.index("end") + 1):
        if menu.type(index) != "separator" and menu.entrycget(index, "label") == label:
            return index
    raise AssertionError(f"no {label!r} in {_labels(menu)}")


# -- where it appears ------------------------------------------------------------


def test_right_clicking_an_element_offers_its_menu(designer):
    posted = _right_click(designer, _centre(designer, "go"))
    assert len(posted) == 1


def test_it_selects_what_was_right_clicked(designer):
    _right_click(designer, _centre(designer, "edt"))
    assert designer.selected == "edt"


def test_right_clicking_empty_canvas_offers_nothing(designer):
    assert _right_click(designer, (390, 390)) == []


# -- what it lists ---------------------------------------------------------------


def test_the_main_handler_comes_first_then_the_optional_ones(designer):
    menu = handler_menu.build(designer, "go")
    assert _labels(menu)[2:] == [
        ("on_clicked_go", "line 5"),
        "---",
        ("on_hover_go", "create"),
        ("on_motion_go", "create"),
        ("on_key_go", "create"),
    ]


def test_a_box_leads_with_changed(designer):
    menu = handler_menu.build(designer, "edt")
    entries = [e for e in _labels(menu)[2:] if e != "---"]
    assert [name for name, _ in entries] == [
        "on_changed_edt", "on_clicked_edt", "on_hover_edt", "on_motion_edt", "on_key_edt"
    ]


def test_a_label_has_no_main_handler_so_no_divider(designer):
    menu = handler_menu.build(designer, "status")
    assert "---" not in _labels(menu)[2:]
    assert _labels(menu)[2][0] == "on_clicked_status"


# -- the heading -----------------------------------------------------------------


def test_the_heading_names_the_detected_ide(designer, detected):
    detected["id"] = "vscode"
    assert _labels(handler_menu.build(designer, "go"))[0][0] == "Open in VS Code:"


def test_with_nothing_detected_it_asks(designer):
    assert _labels(handler_menu.build(designer, "go"))[0][0] == "<select IDE>"


def test_the_heading_opens_a_choice_of_ides(designer):
    menu = handler_menu.build(designer, "go")
    chooser = menu.nametowidget(menu.entrycget(0, "menu"))
    labels = [chooser.entrycget(i, "label") for i in range(chooser.index("end") + 1)
              if chooser.type(i) != "separator"]
    assert labels[:4] == ["VS Code", "PyCharm", "Sublime Text (not found)", "Notepad++"]
    assert "Default text editor" in labels[-1]
    assert chooser.entrycget(2, "state") == "disabled", "a missing editor cannot be picked"


def test_choosing_overrides_detection_and_is_remembered(designer, detected):
    detected["id"] = "vscode"
    menu = handler_menu.build(designer, "go")
    chooser = menu.nametowidget(menu.entrycget(0, "menu"))
    chooser.invoke(_index(chooser, "PyCharm"))

    assert editors.chosen() == "pycharm"
    assert _labels(handler_menu.build(designer, "go"))[0][0] == "Open in PyCharm:"


def test_the_current_choice_is_ticked(designer, detected):
    detected["id"] = "vscode"
    menu = handler_menu.build(designer, "go")
    chooser = menu.nametowidget(menu.entrycget(0, "menu"))
    assert chooser._iterlab_choice.get() == "vscode"


# -- choosing a handler ----------------------------------------------------------


def test_a_written_handler_opens_at_its_line(designer, detected, opened):
    detected["id"] = "vscode"
    menu = handler_menu.build(designer, "go")
    menu.invoke(_index(menu, "on_clicked_go"))
    assert opened == [("vscode", "demo.py", 5)]


def test_an_unwritten_one_is_written_then_opened_there(designer, detected, opened):
    detected["id"] = "pycharm"
    menu = handler_menu.build(designer, "go")
    menu.invoke(_index(menu, "on_key_go"))

    source = designer.interface.code_path.read_text(encoding="utf-8")
    line = source.splitlines().index("def on_key_go(ev, event):") + 1
    assert opened == [("pycharm", "demo.py", line)]


def test_the_written_code_is_left_alone(designer, detected):
    """Additive only: what was there is still a prefix-by-content of the file."""
    detected["id"] = "vscode"
    before = designer.interface.code_path.read_text(encoding="utf-8")
    menu = handler_menu.build(designer, "go")
    menu.invoke(_index(menu, "on_hover_go"))
    after = designer.interface.code_path.read_text(encoding="utf-8")
    assert after.startswith(before.rstrip("\n"))


def test_with_no_ide_the_file_still_opens_and_the_line_is_told(designer, opened):
    menu = handler_menu.build(designer, "go")
    menu.invoke(_index(menu, "on_clicked_go"))
    assert opened == [(editors.DEFAULT_APP, "demo.py", 5)]
    caption = designer.app._mode_toggle.caption.cget("text")
    assert "line 5" in caption


def test_an_editor_that_fails_is_reported_not_raised(designer, detected, monkeypatch):
    detected["id"] = "vscode"

    def refuse(*args, **kwargs):
        raise editors.EditorUnavailable("VS Code did not start: nope")

    monkeypatch.setattr(editors, "open_at", refuse)
    menu = handler_menu.build(designer, "go")
    menu.invoke(_index(menu, "on_clicked_go"))
    assert "did not start" in designer.app._mode_toggle.caption.cget("text")


def test_a_file_that_does_not_parse_offers_its_error_line(designer, detected, opened):
    detected["id"] = "vscode"
    designer.interface.code_path.write_text("def ok():\n    pass\n\ndef broken(:\n", encoding="utf-8")
    menu = handler_menu.build(designer, "go")
    labels = _labels(menu)
    assert labels[2] == ("demo.py has a syntax error", "line 4")
    assert len(labels) == 3, "no handler can be listed from a file that does not parse"

    menu.invoke(2)
    assert opened == [("vscode", "demo.py", 4)]
