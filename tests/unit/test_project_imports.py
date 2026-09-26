"""A researcher's own helper modules: importable, and picked up by Hard reset.

Two defects, found together while checking the guide against the code.

The first: `import helper` beside `demo.py` worked when the file was run from an
IDE, where Python puts the script's folder on the path, and failed with
ModuleNotFoundError under the `iterlab` command, where nothing does. The same
file must behave the same however it was opened.

The second: the guide said an edited helper takes effect after Hard reset. It
did not. Hard reset forgot the researcher's own module, and the helper stayed
in `sys.modules` - so `import helper` handed back the old code.

The hazard in fixing the second is the obvious fix. A project's `.venv` usually
lives inside the project folder, and "forget everything under the folder" would
make Python re-import numpy over live C extensions. Those tests are here too.

No GUI: the button's own wiring is tested with the button, in the ui suite.
"""

import sys
import time
import uuid

import pytest

from iterlab.runtime.loader import ModuleLoader, forget, forget_project_modules


@pytest.fixture
def clean_imports(monkeypatch):
    """Undo every change a test makes to the import machinery.

    The loader inserts the project folder into `sys.path` - that is the fix -
    so without this, each test's temporary folder would stay on the path for
    the rest of the run and could shadow another test's module.
    """
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        sys.modules.pop(name, None)


def _unique(prefix="helper"):
    """A module name no other test, and nothing installed, can share."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _project(tmp_path, helper_name, answer="v1"):
    (tmp_path / f"{helper_name}.py").write_text(
        f"def answer():\n    return {answer!r}\n", encoding="utf-8"
    )
    code = tmp_path / "demo.py"
    code.write_text(
        f"import {helper_name}\n\n\ndef on_clicked_go(ev):\n    return {helper_name}.answer()\n",
        encoding="utf-8",
    )
    return code


# -- importable, however it was launched -----------------------------------


def test_a_helper_beside_the_code_imports_without_the_folder_on_the_path(
    tmp_path, monkeypatch, clean_imports
):
    """The `iterlab demo` case: launched from somewhere else entirely."""
    name = _unique()
    code = _project(tmp_path, name)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert str(tmp_path) not in sys.path

    loader = ModuleLoader(code)
    assert loader.refresh(), f"load failed: {loader.load_error}"
    assert loader.resolve("on_clicked_go")(None) == "v1"


def test_the_project_folder_goes_first_as_python_itself_would(tmp_path, clean_imports):
    """`python demo.py` puts the script's folder first; iterlab must match it."""
    code = _project(tmp_path, _unique())
    ModuleLoader(code).refresh()
    assert sys.path[0] == str(tmp_path.resolve())


def test_it_is_added_once_however_often_the_file_reloads(tmp_path, clean_imports):
    code = _project(tmp_path, _unique())
    loader = ModuleLoader(code)
    for _ in range(3):
        loader._load()
    assert sys.path.count(str(tmp_path.resolve())) == 1


# -- and picked up by a restart --------------------------------------------


def test_forgetting_the_project_picks_up_an_edited_helper(tmp_path, clean_imports):
    """What Hard reset now does, and what it used to leave undone."""
    name = _unique()
    code = _project(tmp_path, name, answer="v1")
    loader = ModuleLoader(code)
    loader.refresh()
    assert loader.resolve("on_clicked_go")(None) == "v1"

    time.sleep(0.01)
    (tmp_path / f"{name}.py").write_text("def answer():\n    return 'v2'\n", encoding="utf-8")

    forget(code)
    forgotten = forget_project_modules(tmp_path)
    assert name in forgotten

    fresh = ModuleLoader(code)
    fresh.refresh()
    assert fresh.resolve("on_clicked_go")(None) == "v2"


def test_forgetting_only_the_code_file_was_not_enough(tmp_path, clean_imports):
    """The defect, kept as a test: the helper survives a plain `forget`."""
    name = _unique()
    code = _project(tmp_path, name, answer="v1")
    ModuleLoader(code).refresh()

    time.sleep(0.01)
    (tmp_path / f"{name}.py").write_text("def answer():\n    return 'v2'\n", encoding="utf-8")
    forget(code)

    fresh = ModuleLoader(code)
    fresh.refresh()
    assert fresh.resolve("on_clicked_go")(None) == "v1", "this is why the fix exists"


# -- and what must never be forgotten --------------------------------------


def test_a_module_from_outside_the_project_is_kept(tmp_path, clean_imports):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "shared"
    outside.mkdir()
    name = _unique("shared")
    (outside / f"{name}.py").write_text("X = 1\n", encoding="utf-8")
    sys.path.insert(0, str(outside))
    __import__(name)

    forget_project_modules(project)
    assert name in sys.modules


def test_an_installed_package_inside_the_project_venv_is_kept(tmp_path, clean_imports):
    """The hazard. A `.venv` inside the project must not be treated as the project.

    Forgetting numpy or matplotlib there would make Python re-import them over
    live C extensions - a crash, where the button promises a restart.
    """
    site = tmp_path / ".venv" / "Lib" / "site-packages"
    site.mkdir(parents=True)
    name = _unique("installed")
    (site / f"{name}.py").write_text("X = 1\n", encoding="utf-8")
    sys.path.insert(0, str(site))
    __import__(name)

    forgotten = forget_project_modules(tmp_path)
    assert name in sys.modules
    assert name not in forgotten


def test_the_interpreter_s_own_library_is_never_forgotten(clean_imports):
    """Even pointed straight at the interpreter's own folder."""
    import json  # noqa: F401 - the point is that it stays loaded

    forget_project_modules(sys.prefix)
    assert "json" in sys.modules


def test_iterlab_itself_is_never_forgotten(clean_imports):
    """Even when the project folder contains iterlab, as a checkout of it does."""
    from pathlib import Path

    import iterlab

    containing = Path(iterlab.__file__).resolve().parents[1]
    forgotten = forget_project_modules(containing)
    assert not [name for name in forgotten if name.split(".")[0] == "iterlab"]
    assert "iterlab.runtime.loader" in sys.modules
