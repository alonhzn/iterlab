"""Every mouse button reaches the handler, and the event says which.

Tk's `command` option fires only for button 1, so a button wired through
`command` alone silently ignores middle and right clicks — the handler is never
called at all, rather than called with the wrong value.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

RECORD = """
def on_startup(ev):
    ev.seen = []

def on_clicked_go(ev, event):
    ev.seen.append(event.button)
"""


@pytest.fixture
def gui(mapped, make_app):
    """A real, mapped window.

    Tk delivers synthesised button events only to a viewable widget, so an
    unmapped window silently swallows them — which would make these tests pass
    against a button that ignores the middle and right buttons entirely.
    """
    app = make_app()
    app.built.palette.selected.set("button")
    app.built.create_element("button", Rect(0.1, 0.1, 0.3, 0.15), tag="go")
    app.interface.code_path.write_text(RECORD, encoding="utf-8")
    app.toggle()
    app.root.update()
    return app


def _widget(gui):
    return gui.built.handles["go"].widget


def test_left_click_reports_left(gui):
    _widget(gui).invoke()
    assert gui.built.ev.seen == ["left"]


@pytest.mark.parametrize(
    "sequence, expected",
    [("<ButtonRelease-2>", "middle"), ("<ButtonRelease-3>", "right")],
)
def test_middle_and_right_reach_the_handler(gui, sequence, expected):
    _widget(gui).event_generate(sequence)
    gui.root.update()
    assert gui.built.ev.seen == [expected], (
        f"{expected} click never reached the handler"
    )


def test_all_three_buttons_are_distinguishable(gui):
    widget = _widget(gui)
    widget.invoke()
    widget.event_generate("<ButtonRelease-2>")
    widget.event_generate("<ButtonRelease-3>")
    gui.root.update()
    assert gui.built.ev.seen == ["left", "middle", "right"]


def test_a_left_click_fires_exactly_once(gui):
    """`command` and a <ButtonRelease-1> binding would both fire."""
    _widget(gui).invoke()
    gui.root.update()
    assert gui.built.ev.seen == ["left"], "the handler ran more than once"


def test_the_button_binds_the_extra_mouse_buttons(gui):
    """Wiring, not just mechanism — the recurring defect in this project."""
    bound = set(_widget(gui).bind())
    assert "<ButtonRelease-2>" in bound
    assert "<ButtonRelease-3>" in bound


def test_a_plot_area_also_reports_the_button(gui):
    """The plot path maps matplotlib's MouseButton enum to the same names."""
    from iterlab.ui.elements import _MPL_BUTTON
    from matplotlib.backend_bases import MouseButton

    assert _MPL_BUTTON[MouseButton.LEFT] == "left"
    assert _MPL_BUTTON[MouseButton.MIDDLE] == "middle"
    assert _MPL_BUTTON[MouseButton.RIGHT] == "right"
