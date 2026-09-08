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


def test_a_missing_icon_file_never_takes_the_window_down(make_app, monkeypatch):
    """Decoration must not be able to end a session."""
    from pathlib import Path

    app = make_app()
    monkeypatch.setattr(icon, "PNG", Path("nowhere/absent.png"))
    monkeypatch.setattr(icon, "ICO", Path("nowhere/absent.ico"))
    assert icon.apply(app.root) is False
    assert app.root.winfo_exists()


def test_the_photo_reference_is_held(make_app):
    """Tk drops a collected PhotoImage back to the default without a word."""
    app = make_app()
    icon.apply(app.root)
    assert icon._keep, "nothing is holding the PhotoImage alive"
