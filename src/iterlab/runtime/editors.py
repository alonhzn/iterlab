"""Opening the researcher's code at a handler, in the editor they already use.

There is no command every IDE understands, and no extension is needed either:
each editor worth supporting takes a file and a line on its own command line,
and routes that to the window already open. What varies is the spelling:

    VS Code      code --goto demo.py:42
    PyCharm      pycharm64.exe --line 42 demo.py
    Sublime      subl demo.py:42
    Notepad++    notepad++.exe -n42 demo.py

So the work here is knowing which one to ask. In order:

1. **What the researcher chose.** Remembered outside the project, beside the file
   selectors' memory, and it wins over everything else: detection is a guess,
   and a guess must never override an answer.
2. **What launched iterlab.** Usually the IDE itself - its run button or its
   terminal - and both leave traces: VS Code sets `TERM_PROGRAM=vscode`, PyCharm
   sets `PYCHARM_HOSTED`, and either one is among this process's ancestors.
3. **Nothing.** The caller offers a choice rather than guessing further.

Finding the program to run is separate from knowing which editor it is. The
command-line launcher is looked for on PATH, then where each editor installs
itself, then beside the running editor found among the ancestors - which is
what makes PyCharm work on Windows, where its launcher is rarely on PATH.

Nothing here raises on the researcher's account except `open_at`, whose caller
reports the failure: an editor that will not start is worth a sentence, never a
lost session.

No GUI imports.
"""

from __future__ import annotations

import ast
import glob
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import remembered

#: The id stored for "the system's default text editor": opens the file, and
#: cannot go to a line. Always available, so there is always something to pick.
DEFAULT_APP = "default"

#: The name the choice is remembered under.
PREFERENCE = "editor"


class EditorUnavailable(Exception):
    """The chosen editor could not be started, with a reason worth showing."""


@dataclass(frozen=True)
class Editor:
    id: str
    name: str
    #: Command-line launchers, looked for on PATH.
    launchers: tuple
    #: Where each platform installs it: glob patterns, environment variables
    #: expanded, newest match wins.
    installed: dict
    #: Executable names that identify it among this process's ancestors.
    processes: tuple

    def command(self, launcher, path, line) -> list:
        line = max(int(line or 1), 1)
        path = str(path)
        if self.id == "vscode":
            return [launcher, "--goto", f"{path}:{line}"]
        if self.id == "pycharm":
            return [launcher, "--line", str(line), path]
        if self.id == "sublime":
            return [launcher, f"{path}:{line}"]
        if self.id == "notepadpp":
            return [launcher, f"-n{line}", path]
        raise ValueError(self.id)  # pragma: no cover - closed set


EDITORS = (
    Editor(
        id="vscode",
        name="VS Code",
        launchers=("code",),
        installed={
            "win32": (
                r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
                r"%ProgramFiles%\Microsoft VS Code\bin\code.cmd",
            ),
            "darwin": (
                "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
                "~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
            ),
            "linux": ("/usr/share/code/bin/code", "/snap/bin/code"),
        },
        processes=("code.exe", "code", "electron"),
    ),
    Editor(
        id="pycharm",
        name="PyCharm",
        launchers=("pycharm64", "pycharm", "charm", "pycharm-community", "pycharm-professional"),
        installed={
            "win32": (
                r"%LOCALAPPDATA%\JetBrains\Toolbox\scripts\pycharm*.cmd",
                r"%LOCALAPPDATA%\Programs\PyCharm*\bin\pycharm64.exe",
                r"%ProgramFiles%\JetBrains\PyCharm*\bin\pycharm64.exe",
            ),
            "darwin": (
                "/Applications/PyCharm*.app/Contents/MacOS/pycharm",
                "~/Applications/PyCharm*.app/Contents/MacOS/pycharm",
            ),
            "linux": (
                "~/.local/share/JetBrains/Toolbox/scripts/pycharm*",
                "/snap/bin/pycharm-*",
                "/opt/pycharm*/bin/pycharm.sh",
            ),
        },
        processes=("pycharm64.exe", "pycharm.exe", "pycharm", "pycharm.sh"),
    ),
    Editor(
        id="sublime",
        name="Sublime Text",
        launchers=("subl",),
        installed={
            "win32": (
                r"%ProgramFiles%\Sublime Text\subl.exe",
                r"%ProgramFiles%\Sublime Text 3\subl.exe",
            ),
            "darwin": ("/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl",),
            "linux": ("/opt/sublime_text/sublime_text",),
        },
        processes=("sublime_text.exe", "sublime_text"),
    ),
    Editor(
        id="notepadpp",
        name="Notepad++",
        launchers=("notepad++",),
        installed={
            "win32": (
                r"%ProgramFiles%\Notepad++\notepad++.exe",
                r"%ProgramFiles(x86)%\Notepad++\notepad++.exe",
            ),
        },
        processes=("notepad++.exe",),
    ),
)

BY_ID = {editor.id: editor for editor in EDITORS}


def name_of(editor_id) -> str:
    if editor_id == DEFAULT_APP:
        return "the default text editor"
    editor = BY_ID.get(editor_id)
    return editor.name if editor else str(editor_id)


# -- who launched us ----------------------------------------------------------


def _platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _ancestors_windows(limit):
    import ctypes
    from ctypes import wintypes

    class ENTRY(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    parents = {}
    try:
        entry = ENTRY()
        entry.dwSize = ctypes.sizeof(ENTRY)
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    kernel32.OpenProcess.restype = wintypes.HANDLE
    found, pid = [], parents.get(os.getpid())
    while pid and len(found) < limit:
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if handle:
            try:
                size = wintypes.DWORD(1024)
                buffer = ctypes.create_unicode_buffer(1024)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    found.append(buffer.value)
            finally:
                kernel32.CloseHandle(handle)
        next_pid = parents.get(pid)
        pid = next_pid if next_pid != pid else None
    return found


def _ancestors_linux(limit):
    found, pid = [], os.getppid()
    while pid > 1 and len(found) < limit:
        try:
            found.append(os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            pass
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            # The command name is in parentheses and may contain spaces.
            pid = int(handle.read().rsplit(")", 1)[1].split()[1])
    return found


def _ancestors_ps(limit):
    found, pid = [], os.getppid()
    while pid > 1 and len(found) < limit:
        out = subprocess.run(
            ["ps", "-o", "ppid=", "-o", "comm=", "-p", str(pid)],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        if not out:
            break
        parent, _, command = out.partition(" ")
        found.append(command.strip())
        pid = int(parent)
    return found


def ancestors(limit=16) -> list:
    """Executable paths of this process's parents, nearest first. Never raises."""
    try:
        if sys.platform == "win32":
            return _ancestors_windows(limit)
        if os.path.isdir("/proc"):
            return _ancestors_linux(limit)
        return _ancestors_ps(limit)
    except Exception:
        return []


_PARENTS = None


def _parents() -> list:
    """`ancestors()`, looked up once: a process's parents do not change."""
    global _PARENTS
    if _PARENTS is None:
        _PARENTS = ancestors()
    return _PARENTS


def _named(editor, path) -> bool:
    # Either separator, whatever this platform uses: `Path` on POSIX would not
    # split a Windows path, and the names are all that matter here.
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    return name.lower() in editor.processes


def detect(environ=None, parents=None):
    """Which known editor launched iterlab, or None."""
    environ = os.environ if environ is None else environ
    if environ.get("TERM_PROGRAM") == "vscode" or environ.get("VSCODE_IPC_HOOK_CLI"):
        return "vscode"
    if environ.get("PYCHARM_HOSTED") or environ.get("TERMINAL_EMULATOR", "").startswith("JetBrains"):
        return "pycharm"
    parents = _parents() if parents is None else parents
    for path in parents:
        for editor in EDITORS:
            # "electron" and "code" are too generic on their own to name VS Code.
            if editor.id == "vscode" and "code" not in str(path).lower():
                continue
            if _named(editor, path):
                return editor.id
    return None


# -- the program to run -------------------------------------------------------


def _installed(editor):
    for pattern in editor.installed.get(_platform(), ()):
        expanded = os.path.expanduser(os.path.expandvars(pattern))
        if "%" in expanded:  # a variable this machine does not have
            continue
        matches = sorted(glob.glob(expanded))
        if matches:
            return matches[-1]  # the newest version, as they sort
    return None


def _beside_the_running_one(editor, parents):
    for path in parents:
        if not _named(editor, path):
            continue
        running = Path(path)
        if editor.id == "vscode":
            # The window is Code.exe; the command line lives in bin/ beside it.
            for candidate in ("bin/code.cmd", "bin/code", "Resources/app/bin/code",
                              "../Resources/app/bin/code"):
                launcher = running.parent / candidate
                if launcher.is_file():
                    return str(launcher.resolve())
            continue
        # PyCharm's own executable takes --line and hands it to the open window.
        if running.is_file():
            return str(running)
    return None


def find_launcher(editor, parents=None):
    """A program that opens `editor` at a line, or None."""
    for name in editor.launchers:
        found = shutil.which(name)
        if found:
            return found
    installed = _installed(editor)
    if installed:
        return installed
    return _beside_the_running_one(editor, _parents() if parents is None else parents)


def available(parents=None) -> dict:
    """{editor id: launcher or None} for every known editor."""
    parents = _parents() if parents is None else parents
    return {editor.id: find_launcher(editor, parents) for editor in EDITORS}


# -- the choice ---------------------------------------------------------------


def chosen():
    """The editor the researcher picked, if they have."""
    value = remembered.load_preference(PREFERENCE)
    return value if value in BY_ID or value == DEFAULT_APP else None


def choose(editor_id) -> bool:
    """Remember a pick. Returns whether it reached the disk."""
    if editor_id not in BY_ID and editor_id != DEFAULT_APP:
        raise ValueError(f"unknown editor {editor_id!r}")
    return remembered.remember_preference(PREFERENCE, editor_id)


def current(environ=None, parents=None):
    """(editor id or None, how it was decided: "chosen", "detected" or None)."""
    picked = chosen()
    if picked:
        return picked, "chosen"
    found = detect(environ, parents)
    if found:
        return found, "detected"
    return None, None


# -- where, and going there -----------------------------------------------------


def handler_lines(source) -> dict:
    """{top-level function name: line of its `def`}. Raises SyntaxError."""
    tree = ast.parse(source)
    lines = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # The `def` line, not the first decorator: that is the line a
            # person means by "where the function is".
            lines[node.name] = node.lineno
    return lines


def _no_console():
    # A `.cmd` launcher would otherwise flash a console window on Windows.
    return {"creationflags": 0x08000000} if sys.platform == "win32" else {}


def _open_default(path):
    if sys.platform == "win32":
        # "edit", not the default verb: the default for a .py file is to run it.
        os.startfile(str(path), "edit")
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_at(editor_id, path, line, parents=None, popen=subprocess.Popen) -> None:
    """Open `path` at `line` in `editor_id`. Raises EditorUnavailable."""
    if editor_id == DEFAULT_APP:
        try:
            _open_default(path)
        except Exception as exc:
            raise EditorUnavailable(f"could not open {Path(path).name}: {exc}") from exc
        return
    editor = BY_ID.get(editor_id)
    if editor is None:
        raise EditorUnavailable(f"unknown editor {editor_id!r}")
    launcher = find_launcher(editor, parents)
    if launcher is None:
        raise EditorUnavailable(
            f"{editor.name} was not found. Choose another editor at the top of this menu"
        )
    try:
        popen(
            editor.command(launcher, path, line),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **_no_console(),
        )
    except Exception as exc:
        raise EditorUnavailable(f"{editor.name} did not start: {exc}") from exc
