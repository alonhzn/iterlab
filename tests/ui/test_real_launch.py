"""Real launches: a new Python process, a real window, a real close.

Everything else in the suite opens interfaces inside the test process, against a
shared root, and never exits. That cannot see what happens between one run of
iterlab and the next, and it cannot see `python demo.py` - the IDE's run button -
because the test harness is the one doing the launching.

These were Gate 2 items, on the grounds that only a real close and relaunch
proves the whole path. A subprocess is a real close and relaunch.

The researcher's own `on_startup` drives each run: it is the one piece of code a
launched interface is guaranteed to execute. It acts once the window is up,
waits for anything that acting set in motion, writes what it saw to a probe file
and closes the window. The process then has to exit on its own.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

from iterlab.codegen.templates import starter_file
from iterlab.layout import store
from iterlab.layout.schema import Element, Layout, Rect
from iterlab.ui.app import RESIZE_SAVE_MS

pytestmark = pytest.mark.ui

#: Long enough for a matplotlib import and a window on a slow CI runner; a hang
#: is a failure, not a wait.
TIMEOUT_S = 90

#: When the window is taken to be up.
UP_MS = 300

#: How long after acting before looking: a resize is saved after a pause, and
#: this has to be comfortably longer than that pause.
SETTLE_MS = RESIZE_SAVE_MS * 4

# The on_startup each launch runs. `act` and `look` are filled in per test; both
# write into `record`, which is what the test gets back.
STARTUP = '''
def on_startup(ev):
    import json
    import tkinter

    root = tkinter._default_root
    record = {{}}

    def guarded(step):
        try:
            step()
        except Exception as exc:
            record.setdefault("error", repr(exc))

    def act():
{act}

    def look():
{look}

    def finish():
        guarded(look)
        with open({probe!r}, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        root.destroy()

    root.after({up}, lambda: guarded(act))
    root.after({up} + {settle}, finish)
'''

# Opens the pair the way `run` does, then goes to the editor before acting. The
# researcher's code only ever runs in GUI mode, so the editor needs a driver.
EDITOR_DRIVER = '''
import sys

from iterlab.app import open_interface

app = open_interface(sys.argv[1], _show=False)
app.toggle()
assert app.mode == "editor", app.mode
root = app.root
root.after({up}, lambda: root.geometry("{geometry}"))
root.after({up} + {settle}, root.destroy)
app.run()
'''


@pytest.fixture
def state_home(tmp_path):
    """Keep the launched process's remembered selections out of the real ones."""
    home = tmp_path / "state_home"
    home.mkdir()
    return home


@pytest.fixture
def probe(tmp_path):
    return tmp_path / "probe.json"


def _environment(state_home):
    env = dict(os.environ)
    # Every place remembered.state_dir() may look, on every platform.
    for name in ("LOCALAPPDATA", "APPDATA", "XDG_STATE_HOME", "HOME"):
        env[name] = str(state_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _project(directory, *elements, size=(640, 400)):
    """A pair on disk, drawn the way the editor would have drawn it."""
    directory.mkdir(parents=True, exist_ok=True)
    layout = Layout()
    for element in elements:
        layout.add(element)
    layout.resize(*size)
    store.save(layout, directory / "demo_layout.py")
    (directory / "demo.py").write_text(starter_file("demo"), encoding="utf-8")
    return directory


def _block(source):
    source = textwrap.dedent(source).strip("\n") or "pass"
    return textwrap.indent(source, " " * 8)


def _script(project, probe, act="", look=""):
    """Replace the starter's on_startup with one that acts, reports and closes."""
    code = (project / "demo.py").read_text(encoding="utf-8")
    start = code.index("def on_startup")
    end = code.index('if __name__ == "__main__":')
    startup = STARTUP.format(
        act=_block(act), look=_block(look), probe=str(probe), up=UP_MS, settle=SETTLE_MS
    )
    (project / "demo.py").write_text(
        code[:start] + startup.lstrip("\n") + "\n\n" + code[end:], encoding="utf-8"
    )


def _launch(argv, cwd, state_home):
    finished = subprocess.run(
        [sys.executable, *argv],
        cwd=str(cwd),
        env=_environment(state_home),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
    )
    detail = (
        f"exit {finished.returncode}\n"
        f"stdout:\n{finished.stdout}\nstderr:\n{finished.stderr}"
    )
    assert finished.returncode == 0, detail
    assert "Traceback" not in finished.stderr, detail
    return detail


def _run_demo(project, cwd, state_home, probe, act="", look=""):
    """`python demo.py`, as an IDE's run button does it. Returns the record."""
    _script(project, probe, act=act, look=look)
    if probe.exists():
        probe.unlink()
    detail = _launch([str(project / "demo.py")], cwd, state_home)
    assert probe.exists(), "on_startup never reported back\n" + detail
    record = json.loads(probe.read_text(encoding="utf-8"))
    assert "error" not in record, record.get("error", "") + "\n" + detail
    return record


def _same_place(one, two):
    def norm(path):
        return os.path.normcase(os.path.realpath(str(path)))

    return norm(one) == norm(two)


BUTTON = Element("go", "button", Rect(0.1, 0.1, 0.3, 0.2))

LOOK_AT_SIZE = """
root.update_idletasks()
record["size"] = [root.winfo_width(), root.winfo_height()]
"""


# -- the IDE's run button (Gate 2 #40) ----------------------------------------


def test_running_the_file_opens_the_interface(tmp_path, state_home, probe):
    """`python demo.py`, from any directory, is `iterlab demo`."""
    project = _project(tmp_path / "project", BUTTON)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    record = _run_demo(project, elsewhere, state_home, probe, look="""
        record["has_go"] = hasattr(ev, "go")
        record["mapped"] = bool(root.winfo_ismapped())
        record["title"] = root.title()
    """)

    assert record["has_go"], "the interface ran without the element that was drawn"
    assert record["mapped"], "the window never appeared"
    assert "demo" in record["title"]


# -- the size survives a relaunch (Gate 2 #50, #51, #55) -----------------------


def test_a_resized_interface_reopens_that_size(tmp_path, state_home, probe):
    project = _project(tmp_path / "project", BUTTON)

    _run_demo(project, tmp_path, state_home, probe, act='root.geometry("900x600")')
    record = _run_demo(project, tmp_path, state_home, probe, look=LOOK_AT_SIZE)

    assert record["size"] == [900, 600]


def test_a_resized_editor_reopens_the_interface_that_size(tmp_path, state_home, probe):
    """One size for both modes: resizing the editor sizes the interface."""
    project = _project(tmp_path / "project", BUTTON)
    driver = tmp_path / "drive_editor.py"
    driver.write_text(
        EDITOR_DRIVER.format(up=UP_MS, settle=SETTLE_MS, geometry="1000x640"),
        encoding="utf-8",
    )

    _launch([str(driver), str(project / "demo")], tmp_path, state_home)
    record = _run_demo(project, tmp_path, state_home, probe, look=LOOK_AT_SIZE)

    assert record["size"] == [1000, 640]


def test_the_size_does_not_drift_over_several_relaunches(tmp_path, state_home, probe):
    project = _project(tmp_path / "project", BUTTON)
    _run_demo(project, tmp_path, state_home, probe, act='root.geometry("870x520")')

    sizes = [
        _run_demo(project, tmp_path, state_home, probe, look=LOOK_AT_SIZE)["size"]
        for _ in range(3)
    ]
    assert sizes == [[870, 520]] * 3


# -- a file selector remembers across a relaunch (Gate 2 #36, #37, #38) --------

PICKER = Element("pick", "file_select", Rect(0.1, 0.1, 0.3, 0.2))

# Choose `chosen` through the real widget, with only the OS dialog replaced.
CHOOSE = """
from iterlab.ui import dialogs

dialogs.ask_open_file = lambda **kwargs: {chosen!r}
ev.pick.widget.invoke()
"""

# What a relaunch sees: the remembered path, and where the chooser would open.
# The dialog is cancelled, so nothing is changed by looking.
INSPECT = """
from iterlab.ui import dialogs

record["path"] = ev.pick.path

def cancelled(**kwargs):
    record["opens_in"] = kwargs.get("initial_dir")
    return ""

dialogs.ask_open_file = cancelled
ev.pick.widget.invoke()
"""


@pytest.fixture
def chosen(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    spectrum = data / "spectrum.csv"
    spectrum.write_text("1,2\n", encoding="utf-8")
    return spectrum


def _choose_then_close(project, cwd, state_home, probe, path):
    _run_demo(project, cwd, state_home, probe, act=CHOOSE.format(chosen=str(path)))


def test_a_chosen_file_survives_a_relaunch(tmp_path, state_home, probe, chosen):
    project = _project(tmp_path / "project", PICKER)
    _choose_then_close(project, tmp_path, state_home, probe, chosen)

    record = _run_demo(project, tmp_path, state_home, probe, act=INSPECT)

    assert _same_place(record["path"], chosen)
    # Handed the file itself, which the OS chooser opens beside and selects.
    assert _same_place(record["opens_in"], chosen)


def test_a_deleted_file_reads_as_empty_and_opens_where_it_was(
    tmp_path, state_home, probe, chosen
):
    project = _project(tmp_path / "project", PICKER)
    _choose_then_close(project, tmp_path, state_home, probe, chosen)
    chosen.unlink()

    record = _run_demo(project, tmp_path, state_home, probe, act=INSPECT)

    assert record["path"] == ""
    assert _same_place(record["opens_in"], chosen.parent)


def test_a_moved_project_starts_over_quietly(tmp_path, state_home, probe, chosen):
    """The memory is keyed by where the project lives, so a move forgets it."""
    project = _project(tmp_path / "project", PICKER)
    _choose_then_close(project, tmp_path, state_home, probe, chosen)
    moved = shutil.move(str(project), str(tmp_path / "moved"))

    from pathlib import Path

    record = _run_demo(Path(moved), tmp_path, state_home, probe, act=INSPECT)

    assert record["path"] == ""
    assert not _same_place(record["opens_in"], chosen.parent)


# -- matplotlib is paid for at opening, not at the first switch ----------------

FIRST_SWITCH = r'''
import json
import sys
import tkinter

seen = {}
original = tkinter.Tk.__init__


def recording(self, *args, **kwargs):
    seen["plots_ready_before_the_window"] = "matplotlib.backends.backend_tkagg" in sys.modules
    original(self, *args, **kwargs)


tkinter.Tk.__init__ = recording

from iterlab.app import open_interface

app = open_interface("demo", _show=False)  # a new interface: opens in the editor
seen["mode"] = app.mode
before = set(sys.modules)
app.built.create_element(
    "axes", __import__("iterlab.layout.schema", fromlist=["Rect"]).Rect(0.1, 0.1, 0.8, 0.8)
)
app.toggle()
app.root.update()
seen["imported_by_first_switch"] = sorted(
    m for m in set(sys.modules) - before if m.split(".")[0] == "matplotlib"
)
app.root.destroy()
json.dump(seen, open(sys.argv[1], "w"))
'''


def test_matplotlib_is_imported_before_the_window_not_on_first_run(tmp_path, state_home, probe):
    """The first "Run it" used to carry the matplotlib import, a third of a second."""
    script = tmp_path / "first_switch.py"
    script.write_text(FIRST_SWITCH, encoding="utf-8")
    _launch([str(script), str(probe)], tmp_path, state_home)
    seen = json.loads(probe.read_text(encoding="utf-8"))

    assert seen["mode"] == "editor"
    assert seen["plots_ready_before_the_window"], "matplotlib was not imported before Tk"
    assert seen["imported_by_first_switch"] == [], seen["imported_by_first_switch"]
