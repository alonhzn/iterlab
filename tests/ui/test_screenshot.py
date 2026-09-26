"""Saving a PNG of the interface.

Most of these fake the capture, to test what does not need a screen: what the
file is called, where it lands, that the button reaches it, and that a machine
which cannot grab the screen says so instead of taking the window down. The
last few grab the real screen and read the picture back.
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


# -- the real grab (Gate 2 #26, #27) -------------------------------------------
#
# Everything above fakes the capture. These do not: the window is put on top of
# everything, the real button is pressed, and the PNG is opened and read. CI's
# display job has a screen, so this is no longer a thing only a person can see.
# A machine that genuinely cannot grab the screen skips rather than fails.

MARK = (255, 0, 255)
SPAN = (255, 0, 0)


def _near(pixel, colour, tolerance=40):
    return all(abs(p - c) <= tolerance for p, c in zip(pixel[:3], colour))


@pytest.fixture
def on_screen(mapped, make_app):
    app = make_app()
    app.built.create_element("label", Rect(0.55, 0.55, 0.4, 0.4), tag="mark")
    app.built.create_element("axes", Rect(0.05, 0.05, 0.4, 0.4), tag="plot")
    app.toggle()
    app.built.ev.mark.background = "#ff00ff"
    ax = app.built.ev.plot
    ax.axvspan(1, 2, color="#ff0000")
    ax.set_xlim(0, 10)

    root = app.root
    root.geometry("800x560+40+40")
    root.attributes("-topmost", True)
    root.lift()
    for _ in range(5):
        root.update()
        ax.figure.canvas.draw()
    try:
        screenshot_mod.capture(app.content)
    except screenshot_mod.ScreenshotUnavailable as exc:
        pytest.skip(f"no screen to grab here: {exc}")
    yield app
    root.attributes("-topmost", False)


def _shoot(app):
    from PIL import Image

    _button(app).invoke()
    app.root.update()
    written = sorted(app.interface.dir.glob("*.png"))
    assert written, "pressing Screenshot wrote nothing"
    image = Image.open(written[-1]).convert("RGB")
    written[-1].unlink()  # the next shot in the same second reuses the name
    return image



def _share(image, colour, box):
    """How much of a region (fractions: left, top, right, bottom) is `colour`."""
    width, height = image.size
    left, top, right, bottom = box
    region = image.crop((int(left * width), int(top * height),
                         int(right * width), int(bottom * height)))
    raw = region.tobytes()
    pixels = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    return sum(_near(p, colour) for p in pixels) / len(pixels)


def test_the_picture_is_the_interface_at_its_size_on_screen(on_screen):
    content = on_screen.content
    image = _shoot(on_screen)
    assert image.size == (content.winfo_width(), content.winfo_height()), (
        "the picture is not the size the interface is on screen"
    )


def test_the_picture_has_no_top_bar_and_nothing_shifted(on_screen):
    """An element drawn top-right is top-right in the picture.

    If the top bar were in the picture, or the grab were offset, the label
    would land somewhere else - the region would be the wrong colour.
    """
    image = _shoot(on_screen)
    # The label is at left 0.55..0.95 and, measured from the top, 0.05..0.45.
    assert _share(image, MARK, (0.60, 0.10, 0.90, 0.40)) > 0.95
    # Its edges, a couple of pixels either side: a shift of even a few pixels
    # moves one of them.
    height = image.size[1]
    for y, inside in ((0.05 * height + 3, True), (0.05 * height - 3, False),
                      (0.45 * height - 3, True), (0.45 * height + 3, False)):
        pixel = image.getpixel((int(0.75 * image.size[0]), int(y)))
        assert _near(pixel, MARK) == inside, f"the label's edge is not where it was drawn (y={y:.0f})"


def test_the_picture_shows_the_zoom_on_screen(on_screen):
    """A zoomed plot is captured zoomed: the grab is what you are looking at."""
    # The plot is at left 0.05..0.45 and, from the top, 0.55..0.95; its middle
    # is well inside the axes whatever matplotlib's margins.
    middle = (0.20, 0.70, 0.30, 0.80)
    assert _share(_shoot(on_screen), SPAN, middle) < 0.05, "the span should be off-centre"

    ax = on_screen.built.ev.plot
    ax.set_xlim(1.2, 1.8)
    ax.figure.canvas.draw()
    on_screen.root.update()

    assert _share(_shoot(on_screen), SPAN, middle) > 0.95, "the zoom is not in the picture"
