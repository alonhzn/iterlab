"""The generated file runs from an IDE, and stays tidy as elements are added.

Two things are being protected here. A researcher should be able to press their
IDE's run button on `demo.py` and get their interface, without a terminal and
without remembering a command. And the block that makes that work has to stay at
the bottom, where it reads as the end of the file, however many elements are
drawn afterwards.
"""

import ast

import pytest

from iterlab.codegen import inject, templates
from iterlab.layout.schema import Element, Rect


def _element(tag, kind):
    label = "x" if kind not in ("axes",) else ""
    return Element(tag, kind, Rect(0.1, 0.1, 0.2, 0.05), label=label)


@pytest.fixture
def code(tmp_path):
    path = tmp_path / "demo.py"
    path.write_text(templates.starter_file("demo"), encoding="utf-8")
    return path


def _top_level(source):
    return [
        node.name if hasattr(node, "name") else "if __name__"
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.If))
    ]


# -- the starter file ------------------------------------------------------


def test_the_starter_file_is_valid_python(code):
    compile(code.read_text(encoding="utf-8"), "demo.py", "exec")


def test_it_ends_with_a_main_guard(code):
    assert _top_level(code.read_text(encoding="utf-8"))[-1] == "if __name__"


def test_the_guard_calls_iterlab_run(code):
    source = code.read_text(encoding="utf-8")
    assert "import iterlab" in source
    assert "iterlab.run(__file__)" in source


def test_it_passes_the_file_not_a_name(code):
    """So it works from any working directory, and survives a rename."""
    source = code.read_text(encoding="utf-8")
    assert "iterlab.run(__file__)" in source
    assert 'iterlab.run("demo")' not in source


def test_run_accepts_what_the_guard_passes(tmp_path):
    """The guard hands `run` a .py path; `Interface` has to resolve that."""
    from iterlab.interface import Interface

    interface = Interface.resolve(str(tmp_path / "demo.py"))
    assert interface.name == "demo"
    assert interface.code_path == tmp_path / "demo.py"


def test_the_guard_does_not_fire_when_iterlab_loads_the_module(code):
    """Otherwise opening an interface would open it again, forever.

    iterlab executes the researcher's module under a name of its own, so
    `__name__` is never "__main__" there. Proven by executing the file the way
    the loader does and checking nothing tried to launch.
    """
    from iterlab.runtime.loader import ModuleLoader

    loader = ModuleLoader(code)
    assert loader.refresh() is True
    assert loader.module.__name__ != "__main__"


# -- stubs go above it -----------------------------------------------------


def test_a_stub_lands_above_the_guard(code):
    element = _element("cmd_0", "button")
    inject.append_stub(code, element, templates.default_stub(element))
    order = _top_level(code.read_text(encoding="utf-8"))
    assert order == ["on_startup", "on_clicked_cmd_0", "if __name__"]


def test_the_guard_stays_last_however_many_are_added(code):
    for tag, kind in (
        ("cmd_0", "button"), ("edt_0", "text_box"),
        ("val_0", "number_box"), ("ax_0", "axes"),
    ):
        element = _element(tag, kind)
        inject.append_stub(code, element, templates.default_stub(element))

    source = code.read_text(encoding="utf-8")
    compile(source, "demo.py", "exec")
    assert _top_level(source)[-1] == "if __name__"


def test_the_gap_does_not_grow_with_every_element(code):
    """Two blank lines before the guard, not two more each time."""
    for tag, kind in (("cmd_0", "button"), ("edt_0", "text_box"), ("val_0", "number_box")):
        element = _element(tag, kind)
        inject.append_stub(code, element, templates.default_stub(element))

    source = code.read_text(encoding="utf-8")
    assert "\n\n\n\nif __name__" not in source
    assert "\n\n\nif __name__" in source


def test_a_file_with_no_guard_still_appends_at_the_end(tmp_path):
    """Interfaces made before this existed keep working exactly as they did."""
    path = tmp_path / "old.py"
    path.write_text("def on_startup(ev):\n    pass\n", encoding="utf-8")
    element = _element("cmd_0", "button")
    inject.append_stub(path, element, templates.default_stub(element))
    assert _top_level(path.read_text(encoding="utf-8")) == ["on_startup", "on_clicked_cmd_0"]


def test_a_guard_in_the_middle_is_not_mistaken_for_the_launcher(tmp_path):
    """Only a trailing guard counts; inserting above one mid-file would drop the
    stub into the middle of the researcher's own code."""
    path = tmp_path / "odd.py"
    path.write_text(
        'if __name__ == "__main__":\n    pass\n\n\ndef on_startup(ev):\n    pass\n',
        encoding="utf-8",
    )
    element = _element("cmd_0", "button")
    inject.append_stub(path, element, templates.default_stub(element))
    assert _top_level(path.read_text(encoding="utf-8"))[-1] == "on_clicked_cmd_0"


@pytest.mark.parametrize(
    "guard",
    [
        'if __name__ == "__main__":',
        "if __name__ == '__main__':",
        'if "__main__" == __name__:',
    ],
)
def test_the_guard_is_recognised_however_it_is_written(tmp_path, guard):
    """Matched by structure, not by text, like everything else here."""
    path = tmp_path / "demo.py"
    path.write_text(f"def on_startup(ev):\n    pass\n\n\n{guard}\n    pass\n", encoding="utf-8")
    element = _element("cmd_0", "button")
    inject.append_stub(path, element, templates.default_stub(element))
    assert _top_level(path.read_text(encoding="utf-8"))[-1] == "if __name__"


def test_a_comment_above_the_guard_stays_with_it(tmp_path):
    """An explanation must not be stranded above an unrelated stub."""
    path = tmp_path / "demo.py"
    path.write_text(
        "def on_startup(ev):\n    pass\n\n\n"
        "# launch it from the IDE\nif __name__ == \"__main__\":\n    pass\n",
        encoding="utf-8",
    )
    element = _element("cmd_0", "button")
    inject.append_stub(path, element, templates.default_stub(element))
    source = path.read_text(encoding="utf-8")
    assert "# launch it from the IDE\nif __name__" in source


def test_windows_line_endings_are_preserved(tmp_path):
    """Principle V: adding a stub must not rewrite every line of the file."""
    path = tmp_path / "demo.py"
    path.write_bytes(
        b'def on_startup(ev):\r\n    pass\r\n\r\n\r\nif __name__ == "__main__":\r\n    pass\r\n'
    )
    element = _element("cmd_0", "button")
    inject.append_stub(path, element, templates.default_stub(element))
    raw = path.read_bytes()
    assert b"\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_running_the_file_as_a_script_opens_that_interface(code, monkeypatch):
    """Executed as `__main__`, the guard calls run with this file's own path.

    Executed rather than read: the previous tests only assert the text is there,
    which would still pass if the call were misspelled or the guard mis-nested.
    Nothing is opened - `run` is replaced, so no window appears and no event loop
    starts.
    """
    import runpy

    import iterlab

    opened = []
    monkeypatch.setattr(iterlab, "run", lambda target: opened.append(str(target)))

    runpy.run_path(str(code), run_name="__main__")

    assert len(opened) == 1, "the guard did not run exactly once"
    assert opened[0].endswith("demo.py")


def test_importing_the_file_normally_opens_nothing(code, monkeypatch):
    """The guard is what stops iterlab's own load from re-launching."""
    import runpy

    import iterlab

    opened = []
    monkeypatch.setattr(iterlab, "run", lambda target: opened.append(str(target)))

    runpy.run_path(str(code), run_name="_iterlab_user_demo")

    assert opened == [], "loading the module tried to open an interface"
