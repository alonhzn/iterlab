"""Generate the iterlab application icon.

Kept in the repository as the *source* of the icon rather than a binary someone
would have to open an image editor to change. Regenerate with:

    python tools/make_icon.py

The idea: a plot, and a loop. A curve rising to the right is every plotting
library's icon; the circular arrow is what makes it this one, because iterating
inside the interface rather than re-running a script is the whole product.

The two marks are kept apart rather than overlaid. An earlier attempt drew the
loop around the curve and the result was a tangle at any size below 128 px -
an icon is read at 32.

Everything is drawn at 8x and downsampled, which is what makes the diagonals
clean rather than aliased. Strokes are brushed as overlapping discs instead of
`draw.line`, which gives real round caps and joins at any width.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
SCALE = 8
S = SIZE * SCALE

BACKDROP = (23, 29, 43, 255)     # deep slate: an app tile, not a document
AXIS = (86, 98, 122, 255)
CURVE = (88, 166, 255, 255)      # the data: cold, and the brightest thing here
LOOP = (255, 184, 76, 255)       # the iteration: warm, so the two never merge
DOT = (255, 255, 255, 255)

MARGIN = int(S * 0.05)
RADIUS = int(S * 0.22)


def stroke(draw, points, colour, width):
    """A thick line with round caps and joins, brushed as overlapping discs.

    `draw.line(..., joint="curve")` leaves notches where segments meet at a
    sharp angle, which is exactly where this curve turns.
    """
    r = width / 2
    for x, y in points:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)


def densify(points, step):
    """Resample a path so the brush leaves no gaps between samples."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        distance = math.hypot(x1 - x0, y1 - y0)
        for i in range(max(int(distance / step), 1)):
            t = i / max(int(distance / step), 1)
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out.append(points[-1])
    return out


def _tile(draw):
    draw.rounded_rectangle(
        [MARGIN, MARGIN, S - MARGIN, S - MARGIN], radius=RADIUS, fill=BACKDROP
    )


def _axes(draw):
    """An L, inset from the tile so it reads as axes rather than a border."""
    x0, y0 = int(S * 0.235), int(S * 0.20)
    x1, y1 = int(S * 0.80), int(S * 0.755)
    width = int(S * 0.030)
    stroke(draw, densify([(x0, y0), (x0, y1)], width / 3), AXIS, width)
    stroke(draw, densify([(x0, y1), (x1, y1)], width / 3), AXIS, width)


def spline(controls, steps=24):
    """Catmull-Rom through the control points, so the curve reads as measured.

    A formula produced a line that was very nearly straight, which is the one
    thing a data curve must not be - a straight diagonal is an arrow, not a
    plot. Control points make the shape a decision rather than an accident.
    """
    pts = [controls[0]] + list(controls) + [controls[-1]]
    out = []
    for p0, p1, p2, p3 in zip(pts, pts[1:], pts[2:], pts[3:]):
        for i in range(steps):
            t = i / steps
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    out.append(controls[-1])
    return out


def _curve(draw, weight=1.0, inset=False):
    """Data: a dip, a recovery, a rise. Shaped, not sloped."""
    if inset:
        # With nothing else on the tile the curve can use the whole of it.
        x0, y0 = int(S * 0.20), int(S * 0.72)
        span_x, span_y = int(S * 0.62), int(S * 0.44)
    else:
        x0, y0 = int(S * 0.235), int(S * 0.755)
        span_x, span_y = int(S * 0.565), int(S * 0.505)
    width = int(S * 0.052 * weight)

    # Normalised (x along the axis, height above it).
    controls = [
        (0.04, 0.20),
        (0.26, 0.46),
        (0.46, 0.24),
        (0.70, 0.64),
        (0.97, 0.95),
    ]
    points = spline([(x0 + cx * span_x, y0 - cy * span_y) for cx, cy in controls])
    stroke(draw, densify(points, width / 4), CURVE, width)
    end = points[-1]
    r = int(S * 0.045 * weight)
    draw.ellipse([end[0] - r, end[1] - r, end[0] + r, end[1] + r], fill=DOT)


def _loop(draw, scale=1.0):
    """A circular arrow, sitting clear of the curve in the upper left.

    Placed in the space the curve leaves empty, which is what lets both marks
    stay legible when the icon is 32 px across.
    """
    cx, cy = int(S * 0.345), int(S * 0.315)
    r = int(S * 0.108 * scale)
    width = int(S * 0.046 * scale)

    # Most of a circle, so it reads as a loop rather than a hook. The gap is
    # what the arrow head fills; a full ring would just be a letter O.
    start, end = math.radians(-55), math.radians(240)
    steps = 120
    points = [
        (cx + r * math.cos(start + (end - start) * i / steps),
         cy + r * math.sin(start + (end - start) * i / steps))
        for i in range(steps + 1)
    ]
    stroke(draw, densify(points, width / 4), LOOP, width)

    # Head at the end of the sweep, pointing the way the arc travels.
    angle = end
    px, py = cx + r * math.cos(angle), cy + r * math.sin(angle)
    head = int(S * 0.070 * scale)
    tangent = angle + math.pi / 2
    draw.polygon(
        [
            (px + head * math.cos(tangent), py + head * math.sin(tangent)),
            (px + head * 0.70 * math.cos(tangent + 2.35),
             py + head * 0.70 * math.sin(tangent + 2.35)),
            (px + head * 0.70 * math.cos(tangent - 2.35),
             py + head * 0.70 * math.sin(tangent - 2.35)),
        ],
        fill=LOOP,
    )


#: Detail levels. An icon is not one drawing scaled - below about 48 px the
#: thin marks close up into mud, so the small sizes get less to say and say it
#: with a fatter brush. This is what an icon set is for, and Pillow will store
#: genuinely different artwork per size inside one .ico.
FULL, MEDIUM, TINY = "full", "medium", "tiny"


def render(detail=FULL, size=SIZE) -> Image.Image:
    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _tile(draw)
    if detail == FULL:
        # Everything: axes, the loop, the data.
        _axes(draw)
        _loop(draw)
        _curve(draw)
    elif detail == MEDIUM:
        # The axes are the first thing to go: they are the quietest mark and
        # the one that costs the most contrast when it starts to blur.
        _loop(draw, scale=1.12)
        _curve(draw, weight=1.22)
    else:
        # At 16 px only one idea survives, and it is the data.
        _curve(draw, weight=1.75, inset=True)
    return image.resize((size, size), Image.LANCZOS)


def detail_for(size):
    if size >= 48:
        return FULL
    if size >= 24:
        return MEDIUM
    return TINY


def main():
    assets = Path(__file__).resolve().parent.parent / "src" / "iterlab" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    render(FULL).save(assets / "iterlab.png")

    # Every size Windows actually asks for, each drawn for the size it is.
    sizes = [256, 128, 64, 48, 32, 24, 16]
    images = [render(detail_for(s), s) for s in sizes]
    images[0].save(
        assets / "iterlab.ico",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"wrote {assets / 'iterlab.png'}")
    print(f"wrote {assets / 'iterlab.ico'}  ({len(sizes)} sizes, 3 detail levels)")


if __name__ == "__main__":
    main()
