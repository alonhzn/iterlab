"""A new project opens at half the screen, an old one at whatever it was left.

The default used to be a fixed 800x450, which is a dialog on most monitors and
a postage stamp on a large one. A size relative to the screen is the only one
that can be right for both.

Only at creation. An existing project's size is the researcher's, and the
commonest way to ruin that would be to "helpfully" reset it on every open.
"""

import pytest

from iterlab.app import open_interface
from iterlab.interface import Interface
from iterlab.layout import store
from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui


@pytest.fixture
def fresh(mapped, make_app):
    """A project that did not exist a moment ago."""
    return make_app("brand_new")


def _half_screen(app):
    return app.root.winfo_screenwidth() // 2, app.root.winfo_screenheight() // 2


# -- a new project ---------------------------------------------------------


def test_the_window_is_half_the_screen(fresh):
    fresh.root.update()
    assert (fresh.root.winfo_width(), fresh.root.winfo_height()) == _half_screen(fresh)


def test_the_interface_is_that_less_the_top_bar(fresh):
    """What is stored is the interface, and the top bar is iterlab's own."""
    width, height = _half_screen(fresh)
    assert fresh.interface.layout.window.width == width
    assert fresh.interface.layout.window.height == height - fresh.chrome_height()


def test_it_is_written_down_not_just_applied(fresh):
    """A second process reads the file, so the file has to know."""
    saved = store.load(fresh.interface.layout_path)
    assert saved.window == fresh.interface.layout.window


def test_it_is_bigger_than_the_old_fixed_default(fresh):
    """The point of the change, on any ordinary screen."""
    if fresh.root.winfo_screenwidth() < 1600:
        pytest.skip("a small screen cannot show the difference")
    assert fresh.interface.layout.window.width > 800


# -- but never an existing one ---------------------------------------------


def test_reopening_keeps_the_size_it_was_left_at(mapped, make_app):
    """The researcher's size survives, which is the whole of the other feature."""
    app = make_app("kept")
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.1))
    app.root.geometry("700x480")
    app.root.update()
    app.remember_size()
    left_at = app.interface.layout.window
    app.close()

    reopened = make_app("kept")
    assert reopened.interface.layout.window == left_at


def test_an_existing_layout_file_is_not_resized_on_open(mapped, tk_root, tmp_path, monkeypatch):
    """Even one that happens to be sitting at the old default."""
    monkeypatch.chdir(tmp_path)
    made = Interface(name="old", directory=tmp_path)
    made.ensure_files()                       # created, so it would be sized
    made.load_layout()
    made.layout.resize(800, 450)
    made.save_layout()

    app = open_interface("old", _show=False, _root=tk_root)
    try:
        assert app.interface.layout.window.width == 800
        assert app.interface.layout.window.height == 450
    finally:
        app.close()


# -- and the floor still holds ---------------------------------------------


def test_a_tiny_screen_does_not_produce_a_sliver(mapped, tk_root, tmp_path, monkeypatch):
    """Half of a very small screen is smaller than a window can usefully be."""
    from iterlab.ui.app import MIN_INTERFACE_HEIGHT, MIN_INTERFACE_WIDTH

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tk_root, "winfo_screenwidth", lambda: 320)
    monkeypatch.setattr(tk_root, "winfo_screenheight", lambda: 200)

    app = open_interface("tiny", _show=False, _root=tk_root)
    try:
        assert app.interface.layout.window.width >= MIN_INTERFACE_WIDTH
        assert app.interface.layout.window.height >= MIN_INTERFACE_HEIGHT
    finally:
        app.close()


# -- the seam --------------------------------------------------------------


def test_creating_the_pair_reports_that_it_did(tmp_path):
    """What tells the app this is the moment to choose a size."""
    made = Interface(name="reported", directory=tmp_path)
    assert made.ensure_files() is True
    assert made.ensure_files() is False, "the second call created nothing"


def test_a_missing_code_file_alone_is_not_a_new_project(tmp_path):
    """The layout is what carries the size, so only its absence counts."""
    made = Interface(name="halfthere", directory=tmp_path)
    made.ensure_files()
    made.code_path.unlink()
    assert made.ensure_files() is False
