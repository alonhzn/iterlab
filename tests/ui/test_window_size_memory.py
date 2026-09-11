"""Reopening an interface gives back the size it was left at.

The layout has always carried a `window` size, and nothing ever wrote to it — so
it stayed at the 800x450 default forever and every fresh launch opened there.

The editor appeared to remember, which is what made this easy to miss. It does
not: it is simply forced up to a minimum that makes the palette and properties
panel fit, and that minimum happened to resemble the size people were using.
"""

import pytest

from iterlab.layout.schema import Layout, Rect, Window

pytestmark = pytest.mark.ui


@pytest.fixture
def gui(mapped, make_app):
    """Mapped, because Tk does not resize a withdrawn window.

    `geometry()` on a withdrawn root is remembered but not applied, so
    `winfo_width()` keeps reporting the old size and nothing under test ever
    sees a resize at all.
    """
    app = make_app()
    app.built.create_element("button", Rect(0.1, 0.1, 0.2, 0.05))
    app.toggle()
    return app


def _resize(app, width, height):
    app.root.geometry(f"{width}x{height}")
    app.root.update()
    app.root.update_idletasks()
    assert app.root.winfo_width() == width, "the window did not actually resize"


# -- the model -------------------------------------------------------------


def test_resize_records_the_size():
    layout = Layout(window=Window(800, 450), elements={})
    assert layout.resize(1240, 680) is True
    assert layout.window == Window(1240, 680)


def test_resize_reports_when_nothing_changed():
    """So a Configure storm does not rewrite the file for every pixel."""
    layout = Layout(window=Window(800, 450), elements={})
    assert layout.resize(800, 450) is False


# -- in the running interface ----------------------------------------------


def test_resizing_in_gui_mode_is_remembered(gui):
    _resize(gui, 1240, 680)
    assert gui.remember_size() is True
    assert gui.interface.layout.window == Window(1240, 680)


def test_it_reaches_the_file_not_just_memory(gui):
    """A new process reads the file, which is the whole point."""
    from iterlab.layout import store

    _resize(gui, 1100, 620)
    gui.remember_size()
    assert store.load(gui.interface.layout_path).window == Window(1100, 620)


def test_reopening_gives_back_that_size(gui, make_app):
    """The reported bug, end to end."""
    _resize(gui, 1240, 680)
    gui.remember_size()
    gui.close()

    reopened = make_app()
    reopened.root.update_idletasks()
    assert reopened.mode == "gui", "an interface with elements opens in GUI mode"
    assert reopened.interface.layout.window == Window(1240, 680)


def test_an_unchanged_size_does_not_rewrite_the_layout(gui):
    """Resizing is common; churning the file on every Configure is not free."""
    gui.remember_size()
    before = gui.interface.layout_path.read_bytes()
    assert gui.remember_size() is False
    assert gui.interface.layout_path.read_bytes() == before


def test_a_minimised_window_is_not_recorded(gui, monkeypatch):
    """Tk reports 1x1 for a window that is not on screen.

    Patched through monkeypatch, not by assignment: the root is shared across
    the whole suite, so a stray `winfo_width` left behind makes every later
    test think the window is one pixel wide.
    """
    original = gui.interface.layout.window
    monkeypatch.setattr(gui.root, "winfo_width", lambda: 1)
    monkeypatch.setattr(gui.root, "winfo_height", lambda: 1)
    assert gui.remember_size() is False
    assert gui.interface.layout.window == original


# -- but not from the editor -----------------------------------------------


def test_resizing_the_editor_resizes_the_interface(gui):
    """The two describe one number between them.

    This is the reverse of what it used to be. The editor's window was ignored
    because it held the sidebar *and* a floor of its own, so its size was not
    the interface's size. Now the window is the interface plus the toolbar and
    nothing else, so the interface size can be read straight back out of it.
    """
    gui.toggle()                      # into the editor
    _resize(gui, 1000 + gui.toolbar_allowance(), 560)
    assert gui.remember_size() is True
    assert gui.interface.layout.window == Window(1000, 560)

    gui.toggle()                      # and the interface follows
    gui.root.update_idletasks()
    assert (gui.root.winfo_width(), gui.root.winfo_height()) == (1000, 560)


def test_a_small_interface_survives_a_visit_to_the_editor(gui):
    """The editor no longer has a floor, so it cannot inflate a small interface."""
    _resize(gui, 620, 400)
    gui.remember_size()

    gui.toggle()
    gui.root.update_idletasks()
    gui.toggle()
    gui.root.update_idletasks()

    assert gui.interface.layout.window == Window(620, 400)


# -- the timer cannot outlive the window -----------------------------------


def test_closing_cancels_a_pending_save(gui):
    """A save firing into a destroyed root printed a Tk error on every close."""
    _resize(gui, 1180, 640)
    gui._on_configure(type("E", (), {"widget": gui.root})())
    assert gui._resize_save is not None

    gui.close()
    assert gui._resize_save is None


def test_a_save_into_a_destroyed_window_is_harmless(gui, monkeypatch):
    """It must report nothing saved rather than raising.

    A real close destroys the root and Tk then refuses every query on it. The
    suite owns its root and keeps it alive, so the refusal is simulated here -
    what is under test is that the failure is swallowed and reported, not that
    the root is gone.
    """
    import tkinter

    def gone():
        raise tkinter.TclError('invalid command name ".!frame"')

    monkeypatch.setattr(gui.root, "winfo_width", gone)
    assert gui.remember_size() is False


def test_configure_from_a_child_is_ignored(gui):
    """<Configure> bubbles from every widget; only the window's own matters."""
    gui._resize_save = None
    gui._on_configure(type("E", (), {"widget": gui.content})())
    assert gui._resize_save is None
