"""Creating an interface and dispatching to it — with no display involved."""

import ast

from iterlab.codegen import inject, templates
from iterlab.interface import Interface
from iterlab.layout.schema import Element, Rect
from iterlab.runtime.dispatch import Dispatcher, Event
from iterlab.runtime.environment import Ev
from iterlab.runtime.faults import RecordingFaultSink
from iterlab.runtime.loader import ModuleLoader


def _new(tmp_path, name="demo"):
    interface = Interface(name, tmp_path)
    interface.ensure_files()
    interface.load_layout()
    return interface


def test_opening_an_unknown_name_creates_both_files(tmp_path):
    interface = _new(tmp_path)
    assert interface.layout_path.exists()
    assert interface.code_path.exists()
    assert interface.layout.is_empty


def test_existing_code_file_is_never_overwritten(tmp_path):
    interface = Interface("demo", tmp_path)
    interface.code_path.write_text("# my work\nVALUE = 42\n", encoding="utf-8")
    interface.ensure_files()
    assert interface.code_path.read_text(encoding="utf-8") == "# my work\nVALUE = 42\n"


def test_creating_an_element_appends_exactly_one_stub(tmp_path):
    interface = _new(tmp_path)
    element = Element("run_fit", "button", Rect(0.1, 0.1, 0.2, 0.1), label="Run fit")
    interface.layout.add(element)
    interface.save_layout()
    inject.append_stub(interface.code_path, element, templates.default_stub(element))

    tree = ast.parse(interface.code_path.read_text(encoding="utf-8"))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["on_startup", "on_clicked_run_fit"]


def test_default_stub_is_click_for_both_types_and_nothing_else(tmp_path):
    """FR-017d: exactly one stub per element, and it is the click handler."""
    interface = _new(tmp_path)
    for name, type_ in (("run_fit", "button"), ("spectrum", "axes")):
        element = Element(name, type_, Rect(0.1, 0.1, 0.2, 0.1))
        interface.layout.add(element)
        inject.append_stub(interface.code_path, element, templates.default_stub(element))

    source = interface.code_path.read_text(encoding="utf-8")
    names = [n.name for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)]
    assert names == ["on_startup", "on_clicked_run_fit", "on_clicked_spectrum"]
    for absent in ("on_hover_", "on_motion_", "on_key_"):
        assert absent not in source


def test_appending_twice_does_not_duplicate(tmp_path):
    interface = _new(tmp_path)
    element = Element("run_fit", "button", Rect(0.1, 0.1, 0.2, 0.1))
    stub = templates.default_stub(element)
    assert inject.append_stub(interface.code_path, element, stub) is True
    assert inject.append_stub(interface.code_path, element, stub) is False
    source = interface.code_path.read_text(encoding="utf-8")
    assert source.count("def on_clicked_run_fit") == 1


def test_clicking_runs_the_researchers_handler(tmp_path):
    interface = _new(tmp_path)
    interface.code_path.write_text(
        "def on_startup(ev):\n"
        "    ev.log = []\n"
        "\n"
        "def on_clicked_run_fit(ev, event):\n"
        "    ev.log.append(event.button)\n",
        encoding="utf-8",
    )
    ev, sink = Ev(), RecordingFaultSink()
    dispatcher = Dispatcher(ModuleLoader(interface.code_path), ev, sink)

    assert dispatcher.invoke("on_startup") is True
    assert dispatcher.invoke(
        "on_clicked_run_fit", Event(kind="clicked", tag="run_fit", button="left")
    ) is True

    assert ev.log == ["left"]
    assert sink.faults == []


def test_handler_receives_ev_first_and_event_second(tmp_path):
    interface = _new(tmp_path)
    interface.code_path.write_text(
        "def on_clicked_a(ev, event):\n"
        "    ev.seen = (type(ev).__name__, event.kind, event.x, event.y)\n",
        encoding="utf-8",
    )
    ev = Ev()
    dispatcher = Dispatcher(ModuleLoader(interface.code_path), ev, RecordingFaultSink())
    dispatcher.invoke("on_clicked_a", Event(kind="clicked", tag="a", x=1.5, y=2.5))
    assert ev.seen == ("Ev", "clicked", 1.5, 2.5)


def test_element_is_reachable_from_ev_by_its_designer_name(tmp_path):
    interface = _new(tmp_path)
    interface.code_path.write_text(
        "def on_clicked_a(ev, event):\n    ev.result = ev.spectrum\n", encoding="utf-8"
    )
    ev = Ev()
    handle = object()
    ev._bind_element("spectrum", handle)
    Dispatcher(ModuleLoader(interface.code_path), ev, RecordingFaultSink()).invoke(
        "on_clicked_a", Event(kind="clicked", tag="a")
    )
    assert ev.result is handle


def test_handler_bound_by_name_not_by_function_object(tmp_path):
    """The closure captures strings only, so a reload needs no rebinding (R2)."""
    interface = _new(tmp_path)
    interface.code_path.write_text(
        "def on_clicked_go(ev, event):\n    ev.value = 1\n", encoding="utf-8"
    )
    ev = Ev()
    dispatcher = Dispatcher(ModuleLoader(interface.code_path), ev, RecordingFaultSink())
    callback = dispatcher.handler_for("go", "clicked")
    callback()
    assert ev.value == 1


# -- the after_invoke hook -------------------------------------------------
# Researcher code that plots changes the figure but does not repaint it. The
# runtime imports no GUI module, so it cannot repaint anything itself; it calls
# this hook and the UI layer does the drawing.


def _hooked(tmp_path, source):
    path = tmp_path / "demo.py"
    path.write_text(source, encoding="utf-8")
    calls = []
    ev, sink = Ev(), RecordingFaultSink()
    dispatcher = Dispatcher(
        ModuleLoader(path), ev, sink, after_invoke=lambda: calls.append(1)
    )
    return dispatcher, calls, sink


def test_after_invoke_fires_when_a_handler_runs(tmp_path):
    d, calls, _ = _hooked(tmp_path, "def on_clicked_go(ev, event):\n    ev.n = 1\n")
    d.invoke("on_clicked_go", Event(kind="clicked", tag="go"))
    assert calls == [1], "the UI must get a chance to repaint what the handler drew"


def test_after_invoke_fires_even_when_the_handler_raises(tmp_path):
    """Work done before the exception is still on the figure.

    Hiding it would leave the researcher looking at a stale plot while the
    banner tells them something failed.
    """
    d, calls, sink = _hooked(
        tmp_path,
        "def on_clicked_go(ev, event):\n    ev.drew = True\n    raise ValueError('x')\n",
    )
    d.invoke("on_clicked_go", Event(kind="clicked", tag="go"))
    assert sink.kinds == ["handler_raised"]
    assert calls == [1]


def test_after_invoke_does_not_fire_when_no_handler_is_written(tmp_path):
    """Nothing ran, so nothing can have changed. Motion handlers fire
    constantly; repainting on every one of them would be wasteful."""
    d, calls, _ = _hooked(tmp_path, "def on_startup(ev):\n    pass\n")
    d.invoke("on_clicked_go", Event(kind="clicked", tag="go"))
    assert calls == []


def test_after_invoke_does_not_fire_when_the_module_is_broken(tmp_path):
    d, calls, sink = _hooked(tmp_path, "def on_clicked_go(ev, event)\n    pass\n")
    d.invoke("on_clicked_go", Event(kind="clicked", tag="go"))
    assert sink.kinds == ["load_failed"]
    assert calls == []
