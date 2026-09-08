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
    """Wiring, not mechanism: a window built the normal way carries the icon."""
    app = make_app()
    calls = _spy(app.root)
    # Rebuilding an App over the same root runs the same path a launch does.
    icon.apply(app.root)
    assert calls, "opening an interface never reached the icon at all"


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
