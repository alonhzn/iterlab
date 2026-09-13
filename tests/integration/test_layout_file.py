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

from iterlab.layout import store
from iterlab.layout.schema import (
    ELEMENT_TYPES,
    Element,
    Layout,
    Rect,
    Style,
    Window,
)


def _layout(**types):
    elements = {}
    for index, (tag, kind) in enumerate(types.items()):
        rect = Rect(0.05, 0.05 + index * 0.1, 0.2, 0.08)
        label = "x" if kind != "axes" else ""
        elements[tag] = Element(tag, kind, rect, label=label)
    return Layout(window=Window(800, 450), elements=elements)


# -- what it writes --------------------------------------------------------


def test_each_element_is_declared_with_its_own_type():
    text = store._serialize(_layout(ax_0="axes", cmd_0="button", val_0="number_box"))
    assert '    ax_0: "Axes"' in text
    assert '    cmd_0: "Button"' in text
    assert '    val_0: "NumberBox"' in text


def test_it_imports_only_what_it_uses():
    text = store._serialize(_layout(ax_0="axes"))
    assert "from iterlab.types import Axes" in text
    assert "Button" not in text


def test_it_is_valid_python():
    ast.parse(store._serialize(_layout(ax_0="axes", cmd_0="button")))


def test_an_interface_with_nothing_drawn_is_still_valid():
    """A new project has no elements, and the file must still import."""
    text = store._serialize(_layout())
    ast.parse(text)
    assert "class Ev:" in text


def test_your_own_attributes_are_allowed_for(tmp_path):
    """`ev` is where a researcher keeps their data, not only their elements.

    Without `__getattr__` every `ev.my_cache` reads as an error; without
    `__setattr__` every `ev.my_cache = ...` does. The second was found by
    running a checker over the result rather than by thinking about it.
    """
    text = store._serialize(_layout(ax_0="axes"))
    assert "def __getattr__" in text
    assert "def __setattr__" in text


def test_every_element_type_has_a_name_to_be_declared_as():
    """A type missing from the map loses its completions with nothing to say so."""
    assert set(store.TYPE_NAMES) == set(ELEMENT_TYPES), (
        f"{set(ELEMENT_TYPES) - set(store.TYPE_NAMES)} has no declared type"
    )


def test_the_names_it_writes_are_importable():
    """The generated file says `from iterlab.types import X` - X has to be there."""
    import iterlab.types as public

    for name in store.TYPE_NAMES.values():
        assert hasattr(public, name), name
    assert hasattr(public, store.FALLBACK_TYPE)


def test_an_unknown_element_type_falls_back_rather_than_vanishing(tmp_path):
    """A layout from a newer iterlab still gets a declaration for each element."""
    layout = _layout(ax_0="axes")
    # Bypassing the dataclass check on purpose: this is what an older build
    # meeting a newer file looks like from in here.
    mystery = object.__new__(Element)
    for field, value in (
        ("tag", "mystery"),
        ("type", "from_the_future"),
        ("position", Rect(0.5, 0.5, 0.2, 0.2)),
        ("label", ""),
        ("style", Style()),
        ("extensions", ""),
    ):
        object.__setattr__(mystery, field, value)
    layout.elements["mystery"] = mystery

    text = store._serialize(layout)
    assert f'    mystery: "{store.FALLBACK_TYPE}"' in text
    ast.parse(text)


# -- where it goes ---------------------------------------------------------


def test_it_sits_beside_the_code(tmp_path):
    from iterlab.interface import Interface

    made = Interface(name="demo", directory=tmp_path)
    assert made.layout_path == tmp_path / "demo_layout.py"
    assert made.code_path == tmp_path / "demo.py"


def test_either_half_of_the_pair_names_the_interface(tmp_path):
    """`demo`, `demo.py` and `demo_layout.py` all mean the same interface."""
    from iterlab.interface import Interface

    for given in ("demo", "demo.py", "demo_layout.py", "demo_layout"):
        assert Interface.resolve(str(tmp_path / given)).name == "demo", given


def test_a_round_trip_with_no_edits_is_byte_identical(tmp_path):
    """Diffs should show what someone changed and nothing else."""
    target = tmp_path / "demo_layout.py"
    store.save(_layout(ax_0="axes", cmd_0="button"), target)
    first = target.read_bytes()

    store.save(store.load(target), target)
    assert target.read_bytes() == first


def test_what_was_written_reads_back(tmp_path):
    target = tmp_path / "demo_layout.py"
    store.save(_layout(ax_0="axes", cmd_0="button"), target)
    back = store.load(target)
    assert sorted(back.elements) == ["ax_0", "cmd_0"]
    assert back.elements["cmd_0"].type == "button"


def test_the_declarations_follow_the_elements(tmp_path):
    target = tmp_path / "demo_layout.py"
    store.save(_layout(ax_0="axes"), target)
    store.save(_layout(ax_0="axes", cmd_0="button"), target)
    assert 'cmd_0: "Button"' in target.read_text(encoding="utf-8")


def test_a_removed_element_stops_being_declared(tmp_path):
    target = tmp_path / "demo_layout.py"
    store.save(_layout(ax_0="axes", cmd_0="button"), target)
    store.save(_layout(ax_0="axes"), target)
    assert "cmd_0" not in target.read_text(encoding="utf-8")


# -- and it keeps up with the interface ------------------------------------


@pytest.fixture
def interface(tmp_path):
    from iterlab.interface import Interface

    made = Interface(name="demo", directory=tmp_path)
    made.ensure_files()
    made.load_layout()
    return made


def test_the_pair_is_two_files(interface):
    """What this release is for: the layout and the declarations are one file."""
    names = sorted(p.name for p in interface.dir.iterdir() if p.is_file())
    assert names == ["demo.py", "demo_layout.py"]


def test_saving_the_layout_declares_the_new_element(interface):
    interface.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go"))
    interface.save_layout()
    text = interface.layout_path.read_text(encoding="utf-8")
    assert 'cmd_0: "Button"' in text
    assert "'cmd_0': {'type': 'button'" in text


def test_a_rename_is_reflected_in_both_halves(interface):
    interface.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Go"))
    interface.save_layout()
    interface.layout.retag("cmd_0", "run_fit")
    interface.save_layout()

    text = interface.layout_path.read_text(encoding="utf-8")
    assert 'run_fit: "Button"' in text
    assert "cmd_0" not in text


def test_the_file_a_handler_imports_from_is_the_layout(interface):
    """`from demo_layout import Ev` - one file, both jobs."""
    from iterlab.codegen import inject

    source = interface.code_path.read_text(encoding="utf-8")
    assert "from demo_layout import Ev" in source
    assert inject.has_ev_import(source, interface.code_path)
