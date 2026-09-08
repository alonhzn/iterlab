"""Colours, ttk styling, and the element icons.

Tk's default widgets look like Windows 95 because that is roughly when their
look was set. `ttk` with the `clam` theme is the one combination that is fully
restyleable on every platform, so everything here builds on that.

Icons are drawn as vectors on a small Canvas rather than loaded from image
files or set as text glyphs. Files would mean assets to ship and paths to
resolve; glyphs would mean betting on the platform font having them, and a
missing glyph renders as a hollow box. A drawn icon always looks the same.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# -- palette ---------------------------------------------------------------

BG = "#f5f6f8"          # sidebar and chrome
SURFACE = "#ffffff"      # canvas, entry fields
BORDER = "#dfe3e8"
BORDER_STRONG = "#c4cad2"

TEXT = "#1f2933"
TEXT_MUTED = "#7b8794"

ACCENT = "#2f6feb"       # selection, focus, the active palette card
ACCENT_SOFT = "#e8f0fe"
DANGER = "#c2334d"
DANGER_SOFT = "#fdecef"

# Element fills on the canvas, kept distinct but quiet.
ELEMENT_FILL = {"plot_area": "#dbeafe", "button": "#e9e3fb", "label": "#e7f2e9"}
ELEMENT_EDGE = {"plot_area": "#7ba7f0", "button": "#a48fe0", "label": "#84b795"}

FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_TITLE = ("Segoe UI", 10, "bold")


def apply_theme(root):
    """Restyle ttk once per interpreter. Safe to call repeatedly."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:  # pragma: no cover - clam ships with Tk everywhere
        pass

    root.configure(bg=BG)

    style.configure(".", background=BG, foreground=TEXT, font=FONT)
    style.configure("TFrame", background=BG)
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
    style.configure("Muted.TLabel", background=BG, foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("Error.TLabel", background=BG, foreground=DANGER, font=FONT_SMALL)

    # Flat buttons: no bevel, no 3-D relief, colour changes on hover instead.
    style.configure(
        "TButton",
        background=SURFACE, foreground=TEXT, font=FONT,
        borderwidth=1, relief="flat", padding=(10, 5),
    )
    style.map(
        "TButton",
        background=[("active", ACCENT_SOFT), ("pressed", ACCENT_SOFT)],
        bordercolor=[("!disabled", BORDER_STRONG)],
    )

    style.configure(
        "Accent.TButton",
        background=ACCENT, foreground="#ffffff", font=FONT_BOLD,
        borderwidth=0, relief="flat", padding=(14, 7),
    )
    style.map("Accent.TButton", background=[("active", "#2559c4"), ("pressed", "#2559c4")])

    style.configure(
        "Danger.TButton",
        background=DANGER_SOFT, foreground=DANGER, font=FONT,
        borderwidth=1, relief="flat", padding=(10, 5),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#f9d7de"), ("pressed", "#f9d7de")],
        bordercolor=[("!disabled", "#efbcc6")],
    )

    style.configure(
        "TEntry",
        fieldbackground=SURFACE, foreground=TEXT,
        bordercolor=BORDER_STRONG, lightcolor=BORDER_STRONG, darkcolor=BORDER_STRONG,
        borderwidth=1, relief="flat", padding=4,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        darkcolor=[("focus", ACCENT)],
    )

    style.configure("TSeparator", background=BORDER)
    return style


# -- icons -----------------------------------------------------------------


def _plot_icon(canvas, size, colour):
    """A pair of axes with a line on them."""
    pad = size * 0.18
    canvas.create_line(pad, pad * 0.7, pad, size - pad, fill=colour, width=2)
    canvas.create_line(pad, size - pad, size - pad * 0.7, size - pad, fill=colour, width=2)
    canvas.create_line(
        pad * 1.6, size - pad * 1.9,
        size * 0.44, size * 0.52,
        size * 0.62, size * 0.66,
        size - pad * 1.1, pad * 1.5,
        fill=colour, width=2, smooth=True,
    )


def _button_icon(canvas, size, colour):
    """A button shape: a rounded outline with a label line inside."""
    pad = size * 0.16
    top, bottom = size * 0.28, size * 0.72
    radius = (bottom - top) / 2
    # Tk has no rounded rectangle, so it is a bar between two arcs.
    canvas.create_arc(
        pad, top, pad + radius * 2, bottom,
        start=90, extent=180, style="arc", outline=colour, width=2,
    )
    canvas.create_arc(
        size - pad - radius * 2, top, size - pad, bottom,
        start=270, extent=180, style="arc", outline=colour, width=2,
    )
    canvas.create_line(pad + radius, top, size - pad - radius, top, fill=colour, width=2)
    canvas.create_line(pad + radius, bottom, size - pad - radius, bottom, fill=colour, width=2)
    canvas.create_line(
        size * 0.36, size * 0.5, size * 0.64, size * 0.5, fill=colour, width=2
    )


def _label_icon(canvas, size, colour):
    """Three text rules, the middle one short."""
    for index, (start, end) in enumerate(((0.18, 0.82), (0.18, 0.58), (0.18, 0.74))):
        y = size * (0.32 + index * 0.19)
        canvas.create_line(
            size * start, y, size * end, y, fill=colour, width=2
        )


ICONS = {"plot_area": _plot_icon, "button": _button_icon, "label": _label_icon}


def element_icon(parent, element_type, size=24, colour=TEXT, background=BG):
    """A small Canvas with the element's icon drawn on it."""
    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=background, highlightthickness=0, bd=0,
    )
    painter = ICONS.get(element_type)
    if painter is not None:
        painter(canvas, size, colour)
    return canvas


def trash_icon(parent, size=16, colour=DANGER, background=DANGER_SOFT):
    """A waste basket, for the delete control."""
    canvas = tk.Canvas(
        parent, width=size, height=size, bg=background, highlightthickness=0, bd=0
    )
    lid, body = size * 0.28, size * 0.86
    canvas.create_line(size * 0.16, lid, size * 0.84, lid, fill=colour, width=2)
    canvas.create_line(size * 0.4, size * 0.16, size * 0.6, size * 0.16, fill=colour, width=2)
    canvas.create_line(size * 0.26, lid, size * 0.33, body, fill=colour, width=2)
    canvas.create_line(size * 0.74, lid, size * 0.67, body, fill=colour, width=2)
    canvas.create_line(size * 0.33, body, size * 0.67, body, fill=colour, width=2)
    return canvas
