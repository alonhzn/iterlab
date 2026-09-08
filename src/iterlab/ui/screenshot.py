"""Saving a picture of the interface.

Captures the researcher's interface, not iterlab's furniture: the top bar with
its toggle and reset buttons is this tool's own chrome, and nobody wants it in
the figure they paste into a report. What is grabbed is the content area, which
in GUI mode is exactly what they built.

The file is written beside the interface's own pair rather than through a file
dialog. A dialog would be modal, and a modal in this application blocks the test
suite outright - the same reason element creation does not ask for a name. The
path is reported instead, which costs the researcher one glance and costs the
suite nothing.
"""

from __future__ import annotations

import time
from pathlib import Path


class ScreenshotUnavailable(Exception):
    """Screen capture did not work here, with a reason worth showing."""


def filename_for(name, at=None) -> str:
    """`demo-20260908-142530.png` — sorts chronologically, never collides."""
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(at))
    return f"{name}-{stamp}.png"


def _bounds(widget):
    widget.update_idletasks()
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    width, height = widget.winfo_width(), widget.winfo_height()
    if width <= 1 or height <= 1:
        raise ScreenshotUnavailable(
            "the window has no size on screen yet - nothing to capture"
        )
    return (x, y, x + width, y + height)


def capture(widget):
    """A PIL image of whatever `widget` occupies on screen.

    Deliberately a screen grab rather than a redraw into an off-screen buffer:
    the interface is Tk widgets and an embedded matplotlib canvas, and only the
    screen holds the composite of both. It is also what makes this honest — the
    picture is what the researcher is actually looking at.
    """
    try:
        from PIL import ImageGrab
    except ImportError as exc:  # pragma: no cover - Pillow ships with matplotlib
        raise ScreenshotUnavailable("Pillow is not available") from exc

    bbox = _bounds(widget)
    try:
        # all_screens matters on Windows: without it a window on a second
        # monitor grabs the wrong region rather than failing.
        try:
            image = ImageGrab.grab(bbox=bbox, all_screens=True)
        except TypeError:
            # all_screens is Windows-only; elsewhere the plain call is correct.
            image = ImageGrab.grab(bbox=bbox)
    except Exception as exc:
        # Headless Linux has no display to grab from, and some desktops refuse.
        # Neither is a reason for the interface to go down (Principle III).
        raise ScreenshotUnavailable(f"screen capture failed: {exc}") from exc

    if image is None:
        raise ScreenshotUnavailable("screen capture returned nothing")
    return image


def save(widget, directory, name, at=None) -> Path:
    """Capture `widget` and write it beside the interface. Returns the path."""
    image = capture(widget)
    path = Path(directory) / filename_for(name, at=at)
    image.save(path)
    return path
