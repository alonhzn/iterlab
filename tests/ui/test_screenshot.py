"""Saving a PNG of the interface.

The capture itself is a screen grab, so the interesting tests are the ones that
do not need a screen: what the file is called, where it lands, that the button
reaches it, and that a machine which cannot grab the screen says so instead of
taking the window down.
"""

import pytest

from iterlab.layout.schema import Rect
from iterlab.ui import screenshot as screenshot_mod

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.3, 0.2), tag="go")
    app.toggle()
    return app


def _button(app):
    from tkinter import ttk

    buttons = [
        w for w in app.chrome.winfo_children()
        if isinstance(w, (app.tk.Button, ttk.Button))
        and "Screenshot" in str(w.cget("text"))
    ]
    assert len(buttons) == 1, f"expected one screenshot button, found {len(buttons)}"
    return buttons[0]


def test_the_filename_is_dated_and_sorts_chronologically():
    early = screenshot_mod.filename_for("demo", at=1000000000)
    later = screenshot_mod.filename_for("demo", at=1000003600)
    assert early.startswith("demo-") and early.endswith(".png")
    assert early < later, "names must sort in the order they were taken"


def test_two_screenshots_never_collide():
    a = screenshot_mod.filename_for("demo", at=1000000000)
    b = screenshot_mod.filename_for("demo", at=1000000001)
    assert a != b


def test_the_button_is_in_the_top_bar(gui):
    _button(gui)  # raises if missing


def test_the_button_is_available_in_both_modes(gui):
    assert str(_button(gui).cget("state")) != "disabled"
    gui.toggle()
    assert str(_button(gui).cget("state")) != "disabled"


def test_pressing_it_writes_a_png_beside_the_interface(gui, monkeypatch):
    """The grab is faked; where the file lands is the part under test."""

    class FakeImage:
        def __init__(self):
            self.saved_to = None

        def save(self, path):
            self.saved_to = path
            open(path, "wb").write(b"\x89PNG fake")

    image = FakeImage()
    monkeypatch.setattr(screenshot_mod, "capture", lambda widget: image)

    _button(gui).invoke()
    gui.root.update()

    written = list(gui.interface.dir.glob("*.png"))
    assert len(written) == 1, "exactly one screenshot should have been written"
    assert written[0].name.startswith(gui.interface.name + "-")


def test_it_captures_the_interface_not_the_chrome(gui, monkeypatch):
    """The top bar is iterlab's furniture, and nobody wants it in their figure."""
    grabbed = {}

    class FakeImage:
        def save(self, path):
            open(path, "wb").write(b"fake")

    def record(widget):
        grabbed["widget"] = widget
        return FakeImage()

    monkeypatch.setattr(screenshot_mod, "capture", record)

    _button(gui).invoke()
    gui.root.update()
    assert grabbed["widget"] is gui.content
    assert grabbed["widget"] is not gui.chrome


def test_a_machine_that_cannot_grab_the_screen_says_so(gui, monkeypatch):
    """Headless Linux has no display. That is not a reason to lose the session."""

    def refuse(widget):
        raise screenshot_mod.ScreenshotUnavailable("no display")

    monkeypatch.setattr(screenshot_mod, "capture", refuse)

    result = gui.save_screenshot()
    gui.root.update()

    assert result is None
    assert gui.root.winfo_exists(), "the window went down over a screenshot"
    assert gui.built.banner.visible, "the failure was swallowed silently"


def test_the_caption_says_where_the_file_went(gui, monkeypatch):
    class FakeImage:
        def save(self, path):
            open(path, "wb").write(b"fake")

    monkeypatch.setattr(screenshot_mod, "capture", lambda widget: FakeImage())
    _button(gui).invoke()
    gui.root.update()
    assert "Saved" in gui._mode_toggle.caption.cget("text")


def test_a_window_with_no_size_is_refused_rather_than_grabbed(gui):
    """Grabbing a zero-size region produces a corrupt file, not an error."""
    tiny = gui.tk.Frame(gui.root)
    with pytest.raises(screenshot_mod.ScreenshotUnavailable):
        screenshot_mod.capture(tiny)
