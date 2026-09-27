"""The window carries the iterlab icon, not Tcl's feather."""

import pytest

from iterlab.ui import icon

pytestmark = pytest.mark.ui


def test_the_icon_files_ship_with_the_package():
    assert icon.ICO.exists(), "the .ico is missing from the package"
    assert icon.PNG.exists(), "the .png is missing from the package"


def test_the_ico_carries_every_size_windows_asks_for():
    from PIL import Image

    with Image.open(icon.ICO) as image:
        sizes = {size for size in image.info["sizes"]}
    for expected in ((256, 256), (48, 48), (32, 32), (16, 16)):
        assert expected in sizes, f"{expected} missing from the icon"


def test_the_small_sizes_are_drawn_for_their_size_not_scaled_down():
    """A 16 px frame that is just the 256 resampled would be mud.

    The small frames deliberately carry less: no axes, a fatter brush. So the
    stored frame must differ from a naive downsample of the large one.
    """
    from PIL import Image, ImageChops

    with Image.open(icon.ICO) as image:
        image.size = (16, 16)
        stored = image.convert("RGBA")
    with Image.open(icon.ICO) as image:
        image.size = (256, 256)
        naive = image.convert("RGBA").resize((16, 16), Image.LANCZOS)

    difference = ImageChops.difference(stored, naive).getbbox()
    assert difference is not None, "the 16 px frame is just the big one scaled"


def test_applying_it_to_a_real_window_works(make_app):
    app = make_app()
    assert icon.apply(app.root) is True


def _spy(root):
    """Record which of Tk's two icon mechanisms actually get called."""
    calls = []
    original = {name: getattr(root, name) for name in ("iconbitmap", "iconphoto")}

    def wrap(name):
        def wrapped(*args, **kwargs):
            calls.append(name)
            return original[name](*args, **kwargs)
        return wrapped

    for name in original:
        setattr(root, name, wrap(name))
    return calls


def test_exactly_one_mechanism_is_applied(make_app):
    """Applying both blanks the icon, which is worse than applying neither.

    Tk's `iconbitmap` and `iconphoto` each work alone. Used together on one
    window they do not layer - the title bar shows an empty grey square. This
    shipped, because the test that existed asserted only that `apply` returned
    True, which it happily did while producing nothing anyone wanted to look at.
    """
    app = make_app()
    calls = _spy(app.root)
    icon.apply(app.root)
    assert len(calls) == 1, f"expected one mechanism, got {calls}"


def test_windows_uses_the_ico_so_each_size_gets_its_own_frame(make_app):
    """`iconphoto` would hand Tk the 256 to squeeze down, wasting the small art."""
    import sys

    if sys.platform != "win32":
        pytest.skip("iconbitmap is the Windows path")
    app = make_app()
    calls = _spy(app.root)
    icon.apply(app.root)
    assert calls == ["iconbitmap"]


def test_the_app_actually_applies_it(make_app):
    """Wiring, not mechanism: a window built the normal way carries the icon.

    `test_the_title_bar_shows_the_mark` proves it on screen; this proves the
    App asks for it, from any platform.
    """
    import tkinter

    root = tkinter.Toplevel()
    try:
        calls = _spy(root)
        from iterlab.app import open_interface

        app = open_interface("fresh", _show=False, _root=root)
        assert calls, "opening an interface never reached the icon at all"
        app.close()
    finally:
        root.destroy()


def test_a_window_is_given_the_icon_once(make_app):
    """Each time costs Windows GDI objects that are never given back."""
    app = make_app()
    calls = _spy(app.root)
    for _ in range(3):
        assert icon.apply_once(app.root) is True
    assert calls == [], "the icon was set again on a window that had it"


def test_a_missing_icon_file_never_takes_the_window_down(make_app, monkeypatch):
    """Decoration must not be able to end a session."""
    from pathlib import Path

    app = make_app()
    monkeypatch.setattr(icon, "PNG", Path("nowhere/absent.png"))
    monkeypatch.setattr(icon, "ICO", Path("nowhere/absent.ico"))
    assert icon.apply(app.root) is False
    assert app.root.winfo_exists()


def test_the_photo_path_holds_its_reference(make_app):
    """Tk drops a collected PhotoImage back to the default without a word.

    Exercises that path directly rather than through `apply`, which on Windows
    takes the `.ico` route and never builds a PhotoImage at all.
    """
    app = make_app()
    before = len(icon._keep)
    assert icon._apply_photo(app.root) is True
    assert len(icon._keep) > before, "nothing is holding the PhotoImage alive"


def test_the_smallest_frames_invert_for_contrast():
    """A dark line on a near-white tile has too little ink left at 16 px.

    The tiny frames are a white wave on solid blue instead. Checked by the
    brightness of the tile's own centre-left, which is background in every
    frame - bright in the large ones, dark in the small.
    """
    from PIL import Image

    def corner_brightness(size):
        with Image.open(icon.ICO) as image:
            image.size = (size, size)
            pixel = image.convert("RGB").getpixel((size // 2, size // 8))
        return sum(pixel) / 3

    assert corner_brightness(256) > 200, "the large frame should sit on a light tile"
    assert corner_brightness(16) < 160, "the small frame should be inverted"


# -- what the title bar actually shows (Gate 2 #31) ----------------------------
#
# Tk reports success for an icon that renders as a blank grey square, and for
# one that silently stays the feather, so every check above can pass while the
# title bar is wrong. That is how this shipped broken once. This looks at the
# title bar itself: a real window, in a process of its own - a Tk class icon
# outlives the root that set it, so the shared test root would be looking at
# whatever an earlier test left - grabbed from the screen and searched for the
# mark's own blue. Tk's feather and a grey box both have none of it.

TITLE_BAR = r'''
import ctypes
import sys
import time
from ctypes import wintypes

from PIL import ImageGrab

from iterlab.app import open_interface

app = open_interface("demo", _show=False)
root = app.root
root.geometry("600x300+80+80")
root.attributes("-topmost", True)
for _ in range(5):
    root.update()
    time.sleep(0.1)

user32 = ctypes.windll.user32
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
outer = wintypes.RECT()
user32.GetWindowRect(int(root.wm_frame(), 16), ctypes.byref(outer))
# The left end of the title bar, where the icon sits, above the interface.
width = max(root.winfo_rootx() - outer.left, 0) + 96
ImageGrab.grab(
    bbox=(outer.left, outer.top, outer.left + width, root.winfo_rooty()),
    all_screens=True,
).save(sys.argv[1])
root.destroy()
'''


def _the_marks_blue():
    """The commonest opaque colour in the 16 px frame: the mark's own blue."""
    from collections import Counter

    from PIL import Image

    image = Image.open(icon.ICO)
    image.size = (16, 16)
    raw = image.convert("RGBA").tobytes()
    opaque = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] > 200]
    return Counter(opaque).most_common(1)[0][0]


def test_the_title_bar_shows_the_mark(tmp_path):
    import subprocess
    import sys

    if sys.platform != "win32":
        pytest.skip("the title bar is drawn by the window manager; checked on Windows")
    from PIL import Image

    grab = tmp_path / "title.png"
    script = tmp_path / "grab_title.py"
    script.write_text(TITLE_BAR, encoding="utf-8")
    finished = subprocess.run(
        [sys.executable, str(script), str(grab)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=60,
    )
    assert finished.returncode == 0, finished.stderr

    blue = _the_marks_blue()
    raw = Image.open(grab).convert("RGB").tobytes()
    pixels = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    hits = sum(all(abs(p - q) <= 40 for p, q in zip(pixel, blue)) for pixel in pixels)
    # The 16 px mark is mostly that blue: well over a hundred pixels at 100 %
    # scaling, more above it. The feather and a grey box score none, and the
    # 256 px artwork squeezed into the title bar - what `iconphoto` gives on
    # Windows - is a thin outline scoring about a dozen.
    assert hits >= 60, f"the title bar shows {hits} pixels of the mark's blue"
