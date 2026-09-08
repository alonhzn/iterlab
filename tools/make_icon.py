"""Generate the iterlab application icon.

Kept in the repository as the *source* of the icon rather than a binary someone
would have to open an image editor to change. Regenerate with:

    python tools/make_icon.py

The mark: a signal, ringed by a cycle. It follows a supplied logo - two arcs
chasing each other around a waveform, in a blue running dark to bright through
the turn - and it says the thing this tool is for. The waveform is the
researcher's data; the ring is the loop they work inside.

Two techniques carry it:

* **Angular gradient on the ring, linear on the wave.** The ring's colour turns
  with the ring, which is what makes it read as rotating rather than as two
  static arcs. One flat blue loses that completely.
* **Brushed strokes.** Every line is laid down as overlapping discs rather than
  through `draw.line`, which leaves notches wherever a path turns sharply - and
  this waveform is nothing but sharp turns.

Everything is drawn at 6x into a mask, the gradient is composited through that
mask, and the result is downsampled. The mask is what allows a gradient at all:
ImageDraw cannot fill with one.

Three detail levels across seven sizes. An icon is not one drawing scaled: the
dotted arcs and hollow markers close into mud below about 64 px, so the small
frames carry less, with a fatter brush.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
SCALE = 6
S = SIZE * SCALE

#: The blue the ring turns through, dark into bright.
NAVY = (13, 52, 112)
AZURE = (41, 155, 255)
SKY = (86, 186, 255)

#: A near-white tile rather than the logo's bare white: an icon needs an edge or
#: it dissolves into a light desktop. Light rather than dark because the logo is,
#: and because a taskbar is usually dark - the tile is what makes the mark carry
#: there.
TILE = (250, 251, 253, 255)
TILE_EDGE = (220, 227, 238, 255)

#: The smallest frames invert: a white wave on solid brand blue. A dark line on
#: a near-white tile has almost no ink left to work with at 16 px and goes faint
#: in a taskbar, where the light tile's own edge is also lost. Inverting trades
#: a little consistency between sizes for a mark that can actually be seen -
#: and nobody views the 16 and the 256 side by side.
TINY_TILE = (21, 96, 190, 255)
TINY_WAVE = (255, 255, 255)

MARGIN = int(S * 0.045)
RADIUS = int(S * 0.225)

#: Where each arc begins and ends, in screen degrees (y down). The gradient is
#: mapped onto exactly this sweep, so the two are defined together.
ARC_START, ARC_END = 190.0, 302.0

CENTRE = (S / 2, S / 2)
RING_R = S * 0.335
RING_W = S * 0.050
DOTTED_R = S * 0.240


# -- brushes ---------------------------------------------------------------


def brush(mask, points, width):
    """A thick line with round caps and joins, as overlapping discs."""
    draw = ImageDraw.Draw(mask)
    r = width / 2
    for x, y in points:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=255)


def densify(points, step):
    """Resample a path so the brush leaves no gaps between samples."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(int(math.hypot(x1 - x0, y1 - y0) / step), 1)
        for i in range(steps):
            t = i / steps
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out.append(points[-1])
    return out


def arc_points(centre, radius, start_deg, end_deg, steps=220):
    cx, cy = centre
    a0, a1 = math.radians(start_deg), math.radians(end_deg)
    return [
        (cx + radius * math.cos(a0 + (a1 - a0) * i / steps),
         cy + radius * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]


def spline(controls, steps=26):
    """Catmull-Rom, so the waveform is a shape rather than a formula."""
    pts = [controls[0]] + list(controls) + [controls[-1]]
    out = []
    for p0, p1, p2, p3 in zip(pts, pts[1:], pts[2:], pts[3:]):
        for i in range(steps):
            t = i / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
                       + (-a + 3 * b - 3 * c + d) * t3)
                for a, b, c, d in zip(p0, p1, p2, p3)
            ))
    out.append(controls[-1])
    return out


# -- gradients -------------------------------------------------------------


def _lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def angular_gradient(size):
    """Colour that turns with the ring, so the ring reads as rotating.

    The run repeats twice around, because the mark has two arcs and each should
    travel dark to bright over its own sweep, as the logo's do.
    """
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    cx = cy = size / 2
    #: The colour run is mapped onto the arc's own sweep rather than onto the
    #: whole half-turn, so the tail is fully dark and the head fully bright.
    #: Spread over a half-turn instead, both ends land mid-blue and the arrow
    #: heads - the thing the eye follows - lose their punch.
    span = ARC_END - ARC_START
    for y in range(size):
        for x in range(size):
            degrees = math.degrees(math.atan2(y - cy, x - cx))
            t = (((degrees - ARC_START) % 180.0) / span)
            t = min(max(t, 0.0), 1.0)
            # Eased, so neither end flattens into a band of one blue.
            t = 0.5 - 0.5 * math.cos(t * math.pi)
            pixels[x, y] = _lerp(NAVY, SKY, t)
    return image


def linear_gradient(size, start, end):
    """Left to right, for the waveform: it travels, where the ring turns."""
    image = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(image)
    for x in range(size):
        draw.line([(x, 0), (x, size)], fill=_lerp(start, end, x / max(size - 1, 1)))
    return image


# -- the marks -------------------------------------------------------------


def _ring(mask, heavy=1.0):
    """Two arcs chasing each other, each ending in an arrow head."""
    width = RING_W * heavy
    # Screen space, y down. Each arc sweeps a little under half a turn, leaving
    # the gaps that the dashes and markers live in.
    for base in (0, 180):
        brush(mask, densify(arc_points(CENTRE, RING_R, base + ARC_START,
                                       base + ARC_END), width / 4), width)
        _arrow_head(mask, base + ARC_END, width)


def _arrow_head(mask, angle_deg, width):
    cx, cy = CENTRE
    angle = math.radians(angle_deg)
    px, py = cx + RING_R * math.cos(angle), cy + RING_R * math.sin(angle)
    size = width * 1.6
    tangent = angle + math.pi / 2
    ImageDraw.Draw(mask).polygon(
        [
            (px + size * math.cos(tangent), py + size * math.sin(tangent)),
            (px + size * 0.95 * math.cos(tangent + 2.30),
             py + size * 0.95 * math.sin(tangent + 2.30)),
            (px + size * 0.95 * math.cos(tangent - 2.30),
             py + size * 0.95 * math.sin(tangent - 2.30)),
        ],
        fill=255,
    )


def _dashes(mask):
    """The short detached segments, continuing the ring through its gaps."""
    width = RING_W * 0.92
    for base in (0, 180):
        brush(mask, densify(arc_points(CENTRE, RING_R, base + 150, base + 173,
                                       steps=40), width / 4), width)


def _dotted(mask):
    """Inner dotted arcs: motion, without a second solid line competing."""
    draw = ImageDraw.Draw(mask)
    r = S * 0.0115
    for base in (0, 180):
        for i in range(12):
            angle = math.radians(base + 202 + i * 8.4)
            x = CENTRE[0] + DOTTED_R * math.cos(angle)
            y = CENTRE[1] + DOTTED_R * math.sin(angle)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=255)


def _markers(mask):
    """Filled nodes top and bottom, hollow ones left and right."""
    draw = ImageDraw.Draw(mask)
    r = S * 0.030
    for angle_deg in (270, 90):
        angle = math.radians(angle_deg)
        x = CENTRE[0] + RING_R * math.cos(angle)
        y = CENTRE[1] + RING_R * math.sin(angle)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=255)

    hollow = S * 0.011
    for angle_deg in (180, 0):
        angle = math.radians(angle_deg)
        x = CENTRE[0] + RING_R * math.cos(angle)
        y = CENTRE[1] + RING_R * math.sin(angle)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=255)
        draw.ellipse(
            [x - r + hollow, y - r + hollow, x + r - hollow, y + r - hollow], fill=0
        )


def wave_mask(heavy=1.0, span=0.272, peak_scale=0.150):
    """The signal: quiet, a swing, one tall peak, quiet again.

    Its own mask, so it can take a different gradient from the ring. Width,
    span and height are all explicit rather than derived from each other,
    because each detail level wants a different balance: with the ring gone
    there is room for the wave to grow into.
    """
    mask = Image.new("L", (S, S), 0)
    width = S * 0.046 * heavy
    cx, cy = CENTRE
    half = S * span

    # (fraction across the span, height in units of the peak)
    shape = [
        (-1.00, 0.00), (-0.80, 0.00), (-0.64, 0.16), (-0.48, 0.34),
        (-0.32, -0.24), (-0.14, -0.95), (0.02, -0.10), (0.18, 0.88),
        (0.34, 0.26), (0.50, -0.10), (0.66, 0.00), (0.82, 0.00), (1.00, 0.00),
    ]
    peak = S * peak_scale
    controls = [(cx + fx * half, cy + fy * peak) for fx, fy in shape]
    brush(mask, densify(spline(controls), width / 4), width)
    return mask


# -- assembly --------------------------------------------------------------


FULL, MEDIUM, TINY = "full", "medium", "tiny"


def render(detail=FULL, size=SIZE) -> Image.Image:
    inverted = detail == TINY
    tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle(
        [MARGIN, MARGIN, S - MARGIN, S - MARGIN],
        radius=RADIUS,
        fill=TINY_TILE if inverted else TILE,
        outline=None if inverted else TILE_EDGE,
        width=0 if inverted else int(S * 0.007),
    )

    ring = Image.new("L", (S, S), 0)
    if detail == FULL:
        _ring(ring)
        _dashes(ring)
        _dotted(ring)
        _markers(ring)
        wave = wave_mask()
    elif detail == MEDIUM:
        # The dotted arcs and hollow markers close up first; the two arcs and
        # their heads are what say "cycle", so they are what stays.
        _ring(ring, heavy=1.15)
        wave = wave_mask(heavy=1.18, span=0.300, peak_scale=0.163)
    else:
        # At 16 px one idea survives, and it is the signal.
        ring = None
        wave = wave_mask(heavy=2.05, span=0.360, peak_scale=0.210)

    if ring is not None:
        tile.paste(angular_gradient(S), (0, 0), ring)
    if inverted:
        tile.paste(Image.new("RGB", (S, S), TINY_WAVE), (0, 0), wave)
    else:
        tile.paste(linear_gradient(S, NAVY, AZURE), (0, 0), wave)
    return tile.resize((size, size), Image.LANCZOS)


def detail_for(size):
    """Which drawing a given size gets.

    The thresholds were set by looking at the frames magnified, not guessed.
    At 64 the dotted arcs had already collapsed into a grey fuzz that made the
    whole mark look dirty, so the full drawing starts at 128.
    """
    if size >= 128:
        return FULL
    if size >= 28:
        return MEDIUM
    return TINY


def main():
    assets = Path(__file__).resolve().parent.parent / "src" / "iterlab" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    render(FULL).save(assets / "iterlab.png")

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
