"""A generated stub says what it takes, when the file can say it.

The annotation is what makes `ev.` complete inside a handler. It names `Ev`,
which lives in the generated module beside the pair - so a file that does not
import it must not be given a stub that refers to it.

iterlab does not add that import to a file it did not write. Everything it puts
into the researcher's file is appended, with the existing content left as an
exact prefix, and an import has to go at the top. The guarantee is worth more
than the completion, so the stub adapts instead.
"""

import ast

import pytest

from iterlab.codegen import inject, templates
from iterlab.layout.schema import Element, Rect


def _element(tag="cmd_0", kind="button"):
    return Element(tag, kind, Rect(0.1, 0.1, 0.2, 0.1), label="Go")


WITH_IMPORT = '''from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from demo_ev import Ev


def on_startup(ev: "Ev"):
    pass
'''

WITHOUT_IMPORT = '''def on_startup(ev):
    pass
'''


def _append(tmp_path, source):
    path = tmp_path / "demo.py"
    path.write_text(source, encoding="utf-8")
    element = _element()
    inject.append_stub(path, element, templates.default_stub(element))
    return path.read_text(encoding="utf-8")


def test_a_file_that_imports_ev_gets_an_annotated_stub(tmp_path):
    after = _append(tmp_path, WITH_IMPORT)
    assert 'def on_clicked_cmd_0(ev: "Ev", event):' in after


def test_a_file_that_does_not_gets_a_plain_one(tmp_path):
    """Naming `Ev` there would be an undefined name in their editor."""
    after = _append(tmp_path, WITHOUT_IMPORT)
    assert "def on_clicked_cmd_0(ev, event):" in after
    assert "Ev" not in after


def test_either_way_the_file_still_parses(tmp_path):
    for source in (WITH_IMPORT, WITHOUT_IMPORT):
        ast.parse(_append(tmp_path, source))


def test_nothing_above_the_stub_is_touched(tmp_path):
    """The additive guarantee, which is why the import is never inserted."""
    for source in (WITH_IMPORT, WITHOUT_IMPORT):
        after = _append(tmp_path, source)
        assert after.startswith(source.rstrip("\n")), "existing content must be a prefix"


def test_the_starter_file_can_say_it(tmp_path):
    """A file iterlab wrote has the import, so its stubs are annotated."""
    path = tmp_path / "demo.py"
    templates.write_starter_file(path, "demo")
    source = path.read_text(encoding="utf-8")
    assert inject.has_ev_import(source, path)
    assert 'def on_startup(ev: "Ev")' in source


def test_the_import_is_only_read_by_a_checker(tmp_path):
    """It must cost nothing at launch, and must not need the module to exist."""
    path = tmp_path / "demo.py"
    templates.write_starter_file(path, "demo")
    compiled = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    namespace = {"__name__": "not_main"}
    exec(compiled, namespace)        # no demo_ev.py anywhere: must not raise
    assert "on_startup" in namespace


def test_a_broken_file_reads_as_having_no_import(tmp_path):
    """It cannot be parsed, so nothing can be claimed about what it imports."""
    path = tmp_path / "demo.py"
    assert inject.has_ev_import("def broken(:\n", path) is False


@pytest.mark.parametrize("name", ["demo", "spectra", "my_analysis"])
def test_the_import_name_follows_the_file(tmp_path, name):
    path = tmp_path / f"{name}.py"
    templates.write_starter_file(path, name)
    assert f"from {name}_ev import Ev" in path.read_text(encoding="utf-8")
