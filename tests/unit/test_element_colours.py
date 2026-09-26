"""Every element type can be told apart from every other at a glance.

This was a Gate 2 item on the grounds that "no assertion can judge similarity".
One can: perceptual colour difference is a standard, deterministic measure. CIE
L*a*b* is built so that equal distances look equally different, and a distance
of about 2.3 is the smallest a person can see at all.

The defect that prompted it: the label and the file selector were both the same
pale green, fill and edge, and could only be told apart by reading them.
"""

import itertools

import pytest

from iterlab.layout.schema import ELEMENT_TYPES
from iterlab.ui import theme

#: How far apart two types must be, in the more different of their fill and
#: their edge. A difference a person can see is not one they notice without
#: looking for it; 15 is well clear of that, and the pair that shipped broken
#: was under 7.
AT_A_GLANCE = 15.0


def _lab(colour):
    """sRGB hex -> CIE L*a*b* under D65."""
    h = colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    xyz = (
        (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047,
        (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.00000,
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883,
    )
    fx, fy, fz = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz]
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(one, two):
    """CIE76 colour difference."""
    return sum((p - q) ** 2 for p, q in zip(_lab(one), _lab(two))) ** 0.5


def _apart(fill, edge, a, b):
    return max(delta_e(fill[a], fill[b]), delta_e(edge[a], edge[b]))


def test_the_measure_itself():
    assert delta_e("#ffffff", "#ffffff") == 0
    assert delta_e("#000000", "#ffffff") == pytest.approx(100, abs=0.01)


def test_every_type_has_a_colour():
    assert set(theme.ELEMENT_FILL) == set(ELEMENT_TYPES)
    assert set(theme.ELEMENT_EDGE) == set(ELEMENT_TYPES)


@pytest.mark.parametrize("a, b", list(itertools.combinations(sorted(ELEMENT_TYPES), 2)))
def test_two_types_can_be_told_apart(a, b):
    apart = _apart(theme.ELEMENT_FILL, theme.ELEMENT_EDGE, a, b)
    assert apart >= AT_A_GLANCE, f"{a} and {b} are only {apart:.1f} apart"


def test_the_pair_that_shipped_broken_would_fail():
    """The threshold is only worth something if it rejects the real defect."""
    fill = {"label": "#e7f2e9", "file_select": "#e6f0ea"}
    edge = {"label": "#84b795", "file_select": "#79b394"}
    assert _apart(fill, edge, "label", "file_select") < AT_A_GLANCE
