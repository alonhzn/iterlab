"""The generated module that tells an editor what `ev` holds.

`ev.ax_0.plot(...)` is the single most useful thing an editor could complete for
a researcher, and nothing static can know it: the elements are attached at run
time from the layout. So iterlab writes `<name>_ev.py` beside the pair declaring
them, and annotates the handlers it generates.

That is ordinary typing rather than an editor plugin, which is the point - it
works in whatever people use. The end-to-end proof is a type checker run over a
generated project, which lives in the project's own verification rather than
here: the suite may not depend on mypy being installed.
"""

import ast

import pytest

from iterlab.codegen import evtypes
from iterlab.layout.schema import ELEMENT_TYPES, Element, Layout, Rect, Window


def _layout(**types):
    elements = {}
    for index, (tag, kind) in enumerate(types.items()):
        rect = Rect(0.05, 0.05 + index * 0.1, 0.2, 0.08)
        label = "x" if kind != "axes" else ""
        elements[tag] = Element(tag, kind, rect, label=label)
    return Layout(window=Window(800, 450), elements=elements)


# -- what it writes --------------------------------------------------------


def test_each_element_is_declared_with_its_own_type():
    text = evtypes.render(_layout(ax_0="axes", cmd_0="button", val_0="number_box"))
    assert "    ax_0: Axes" in text
    assert "    cmd_0: Button" in text
    assert "    val_0: NumberBox" in text


def test_it_imports_only_what_it_uses():
    text = evtypes.render(_layout(ax_0="axes"))
    assert "from iterlab.types import Axes" in text
    assert "Button" not in text


def test_it_is_valid_python():
    ast.parse(evtypes.render(_layout(ax_0="axes", cmd_0="button")))


def test_an_interface_with_nothing_drawn_is_still_valid():
    """A new project has no elements, and the file must still import."""
    text = evtypes.render(_layout())
    ast.parse(text)
    assert "class Ev:" in text


def test_your_own_attributes_are_allowed_for(tmp_path):
    """`ev` is where a researcher keeps their data, not only their elements.

    Without `__getattr__` every `ev.my_cache` reads as an error; without
    `__setattr__` every `ev.my_cache = ...` does. The second was found by
    running a checker over the result rather than by thinking about it.
    """
    text = evtypes.render(_layout(ax_0="axes"))
    assert "def __getattr__" in text
    assert "def __setattr__" in text


def test_every_element_type_has_a_name_to_be_declared_as():
    """A type missing from the map loses its completions with nothing to say so."""
    assert evtypes.matches_element_types(), (
        f"{set(ELEMENT_TYPES) - set(evtypes.TYPE_NAMES)} has no declared type"
    )


def test_the_names_it_writes_are_importable():
    """The generated file says `from iterlab.types import X` - X has to be there."""
    import iterlab.types as public

    for name in evtypes.TYPE_NAMES.values():
        assert hasattr(public, name), name
    assert hasattr(public, evtypes.FALLBACK_TYPE)


def test_an_unknown_element_type_falls_back_rather_than_vanishing(tmp_path):
    """A layout from a newer iterlab still gets a declaration for each element."""
    layout = _layout(ax_0="axes")
    # Bypassing the dataclass check on purpose: this is what an older build
    # meeting a newer file looks like from in here.
    layout.elements["mystery"] = object.__new__(Element)
    object.__setattr__(layout.elements["mystery"], "tag", "mystery")
    object.__setattr__(layout.elements["mystery"], "type", "from_the_future")

    text = evtypes.render(layout)
    assert f"    mystery: {evtypes.FALLBACK_TYPE}" in text
    ast.parse(text)


# -- where it goes ---------------------------------------------------------


def test_it_sits_beside_the_pair(tmp_path):
    assert evtypes.path_for(tmp_path / "demo.py") == tmp_path / "demo_ev.py"


def test_the_module_name_is_what_a_handler_imports(tmp_path):
    assert evtypes.module_name_for(tmp_path / "spectra.py") == "spectra_ev"


def test_writing_it_twice_leaves_the_file_alone(tmp_path):
    """No reason to touch it when nothing changed, and an editor notices."""
    layout = _layout(ax_0="axes")
    target = evtypes.write(tmp_path / "demo.py", layout)
    before = target.stat().st_mtime_ns, target.read_bytes()

    evtypes.write(tmp_path / "demo.py", layout)
    assert (target.stat().st_mtime_ns, target.read_bytes()) == before


def test_it_follows_the_elements(tmp_path):
    code = tmp_path / "demo.py"
    evtypes.write(code, _layout(ax_0="axes"))
    evtypes.write(code, _layout(ax_0="axes", cmd_0="button"))
    text = evtypes.path_for(code).read_text(encoding="utf-8")
    assert "cmd_0: Button" in text


def test_a_removed_element_stops_being_declared(tmp_path):
    code = tmp_path / "demo.py"
    evtypes.write(code, _layout(ax_0="axes", cmd_0="button"))
    evtypes.write(code, _layout(ax_0="axes"))
    text = evtypes.path_for(code).read_text(encoding="utf-8")
    assert "cmd_0" not in text


# -- and it keeps up with the interface ------------------------------------


@pytest.fixture
def interface(tmp_path):
    from iterlab.interface import Interface

    made = Interface(name="demo", directory=tmp_path)
    made.ensure_files()
    made.load_layout()
    return made


def test_saving_the_layout_writes_it(interface):
    """Every element change goes through one door, so it cannot fall behind."""
    interface.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go"))
    interface.save_layout()
    assert "cmd_0: Button" in (interface.dir / "demo_ev.py").read_text(encoding="utf-8")


def test_a_rename_is_reflected(interface):
    interface.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go"))
    interface.save_layout()
    interface.layout.retag("cmd_0", "run_fit")
    interface.save_layout()

    text = (interface.dir / "demo_ev.py").read_text(encoding="utf-8")
    assert "run_fit: Button" in text
    assert "cmd_0" not in text


def test_a_folder_that_cannot_be_written_does_not_stop_a_save(interface, monkeypatch):
    """Completions are a convenience. One that can stop a save is not one."""
    from iterlab.codegen import evtypes as module

    def refuse(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(module, "write", refuse)
    interface.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go"))
    interface.save_layout()          # must not raise
    assert "cmd_0" in interface.layout_path.read_text(encoding="utf-8")
