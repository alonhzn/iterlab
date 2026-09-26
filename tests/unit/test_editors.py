"""Which editor to open the code in, how to ask it, and remembering the answer."""

import subprocess

import pytest

from iterlab.runtime import editors, remembered


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(remembered, "state_dir", lambda: tmp_path / "state")
    return tmp_path / "state"


# -- the command each editor understands --------------------------------------


@pytest.mark.parametrize(
    "editor_id, expected",
    [
        ("vscode", ["L", "--goto", "demo.py:42"]),
        ("pycharm", ["L", "--line", "42", "demo.py"]),
        ("sublime", ["L", "demo.py:42"]),
        ("notepadpp", ["L", "-n42", "demo.py"]),
    ],
)
def test_each_editor_is_asked_in_its_own_words(editor_id, expected):
    assert editors.BY_ID[editor_id].command("L", "demo.py", 42) == expected


def test_a_line_below_one_is_the_first_line():
    assert editors.BY_ID["vscode"].command("L", "demo.py", 0)[-1] == "demo.py:1"


# -- detection -----------------------------------------------------------------


@pytest.mark.parametrize(
    "environ, expected",
    [
        ({"TERM_PROGRAM": "vscode"}, "vscode"),
        ({"VSCODE_IPC_HOOK_CLI": "/tmp/vscode-ipc.sock"}, "vscode"),
        ({"PYCHARM_HOSTED": "1"}, "pycharm"),
        ({"TERMINAL_EMULATOR": "JetBrains-JediTerm"}, "pycharm"),
    ],
)
def test_the_ide_is_recognised_by_what_it_sets(environ, expected):
    assert editors.detect(environ=environ, parents=[]) == expected


@pytest.mark.parametrize(
    "parent, expected",
    [
        (r"C:\Program Files\JetBrains\PyCharm 2025.2\bin\pycharm64.exe", "pycharm"),
        (r"C:\Users\me\AppData\Local\Programs\Microsoft VS Code\Code.exe", "vscode"),
        ("/Applications/Visual Studio Code.app/Contents/MacOS/Electron", "vscode"),
        ("/opt/sublime_text/sublime_text", "sublime"),
    ],
)
def test_or_by_being_among_the_ancestors(parent, expected):
    parents = ["/usr/bin/python3", "/bin/bash", parent]
    assert editors.detect(environ={}, parents=parents) == expected


def test_an_electron_app_that_is_not_vscode_is_not_vscode():
    assert editors.detect(environ={}, parents=["/opt/Slack/electron"]) is None


def test_nothing_recognisable_is_nothing():
    assert editors.detect(environ={}, parents=["/bin/bash", "/sbin/init"]) is None


# -- the choice ----------------------------------------------------------------


def test_nothing_is_chosen_at_first():
    assert editors.chosen() is None


def test_a_choice_is_remembered():
    editors.choose("pycharm")
    assert editors.chosen() == "pycharm"


def test_a_choice_wins_over_detection():
    """Detection is a guess; a guess must never override an answer."""
    editors.choose("sublime")
    assert editors.current(environ={"TERM_PROGRAM": "vscode"}, parents=[]) == (
        "sublime", "chosen"
    )


def test_detection_is_used_when_nothing_is_chosen():
    assert editors.current(environ={"PYCHARM_HOSTED": "1"}, parents=[]) == (
        "pycharm", "detected"
    )
    assert editors.current(environ={}, parents=[]) == (None, None)


def test_an_unknown_editor_cannot_be_chosen():
    with pytest.raises(ValueError):
        editors.choose("emacs")


def test_the_default_app_can_be_chosen():
    editors.choose(editors.DEFAULT_APP)
    assert editors.chosen() == editors.DEFAULT_APP


def test_it_lives_beside_the_selectors_memory_without_disturbing_it(tmp_path):
    """Remembered the way a file selector's choice is - and in the same file."""
    interface = tmp_path / "demo_layout.py"
    remembered.remember(interface, "pick", "/data/a.csv")
    editors.choose("vscode")

    assert remembered.load(interface) == {"pick": "/data/a.csv"}
    assert editors.chosen() == "vscode"
    remembered.forget(interface)
    assert editors.chosen() == "vscode"


def test_a_garbled_choice_reads_as_none():
    remembered.remember_preference(editors.PREFERENCE, "not-an-editor")
    assert editors.chosen() is None


# -- finding the program -------------------------------------------------------


def test_the_launcher_on_path_is_used_first(monkeypatch):
    monkeypatch.setattr(editors.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert editors.find_launcher(editors.BY_ID["vscode"], parents=[]) == "/usr/bin/code"


def test_the_running_vscode_offers_its_own_command_line(tmp_path, monkeypatch):
    """Code.exe is the window; the program that takes --goto is bin/code beside it."""
    monkeypatch.setattr(editors.shutil, "which", lambda name: None)
    monkeypatch.setattr(editors, "_installed", lambda editor: None)
    home = tmp_path / "Microsoft VS Code"
    (home / "bin").mkdir(parents=True)
    (home / "Code.exe").write_text("")
    (home / "bin" / "code.cmd").write_text("")

    found = editors.find_launcher(editors.BY_ID["vscode"], parents=[str(home / "Code.exe")])
    assert found is not None and found.lower().endswith("code.cmd")


def test_the_running_pycharm_is_its_own_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(editors.shutil, "which", lambda name: None)
    monkeypatch.setattr(editors, "_installed", lambda editor: None)
    exe = tmp_path / "bin" / "pycharm64.exe"
    exe.parent.mkdir()
    exe.write_text("")
    assert editors.find_launcher(editors.BY_ID["pycharm"], parents=[str(exe)]) == str(exe)


def test_an_editor_nowhere_to_be_found_is_none(monkeypatch):
    monkeypatch.setattr(editors.shutil, "which", lambda name: None)
    monkeypatch.setattr(editors, "_installed", lambda editor: None)
    assert editors.find_launcher(editors.BY_ID["sublime"], parents=[]) is None


def test_the_ancestors_of_this_process_can_be_read():
    """Whatever this runs under - a shell, an IDE, a CI runner - it has a parent."""
    found = editors.ancestors()
    assert found, "the walk up the process tree found nothing"
    assert all(isinstance(path, str) and path for path in found)


# -- opening -------------------------------------------------------------------


def test_opening_runs_the_editors_command(monkeypatch):
    monkeypatch.setattr(editors, "find_launcher", lambda editor, parents=None: "LAUNCHER")
    ran = []
    editors.open_at("pycharm", "demo.py", 7, popen=lambda argv, **kw: ran.append(argv))
    assert ran == [["LAUNCHER", "--line", "7", "demo.py"]]


def test_an_editor_that_is_not_installed_says_so(monkeypatch):
    monkeypatch.setattr(editors, "find_launcher", lambda editor, parents=None: None)
    with pytest.raises(editors.EditorUnavailable, match="not found"):
        editors.open_at("sublime", "demo.py", 1)


def test_an_editor_that_will_not_start_says_so(monkeypatch):
    monkeypatch.setattr(editors, "find_launcher", lambda editor, parents=None: "LAUNCHER")

    def refuse(argv, **kw):
        raise OSError("access denied")

    with pytest.raises(editors.EditorUnavailable, match="did not start"):
        editors.open_at("vscode", "demo.py", 1, popen=refuse)


def test_the_launch_does_not_wait_or_share_our_streams(monkeypatch):
    monkeypatch.setattr(editors, "find_launcher", lambda editor, parents=None: "LAUNCHER")
    seen = {}
    editors.open_at("vscode", "demo.py", 1, popen=lambda argv, **kw: seen.update(kw))
    assert seen["stdout"] is subprocess.DEVNULL and seen["stderr"] is subprocess.DEVNULL


# -- where a handler is --------------------------------------------------------


def test_handler_lines_are_the_def_lines():
    source = "import x\n\n@decorated\ndef on_clicked_go(ev, event):\n    pass\n\ndef helper():\n    def inner():\n        pass\n"
    assert editors.handler_lines(source) == {"on_clicked_go": 4, "helper": 7}


def test_an_unparsable_file_raises_with_its_line():
    with pytest.raises(SyntaxError) as caught:
        editors.handler_lines("def ok():\n    pass\n\ndef broken(:\n")
    assert caught.value.lineno == 4
