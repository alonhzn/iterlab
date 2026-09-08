"""Which mode the single command opens in (FR-001a)."""

from iterlab.app import choose_start_mode
from iterlab.layout.schema import Element, Layout, Rect
from iterlab.ui.app import EDITOR, GUI


def test_empty_interface_opens_in_editor_mode():
    """A new interface has nothing to run, so it opens where work must start."""
    assert choose_start_mode(Layout()) == EDITOR


def test_interface_with_elements_opens_in_gui_mode():
    layout = Layout()
    layout.add(Element("run_fit", "button", Rect(0.1, 0.1, 0.2, 0.1)))
    assert choose_start_mode(layout) == GUI
