"""The layout model, and the rules a layout must satisfy.

No GUI imports. This module is the single source of truth for both the designer
and the runtime (constitution Principle II), which is why it lives outside `ui`.
"""

from __future__ import annotations

import keyword
from dataclasses import dataclass, field, fields, replace

from ..errors import NameInUse, NameInvalid

#: Written into every layout file. Bumped only when the format changes in a way
#: an older build could not read (contracts/layout-schema.md).
SCHEMA_VERSION = 3

#: Element types this build knows. A closed set: an unknown type in a file of a
#: recognized schema version is a defect, not something to skip over.
ELEMENT_TYPES = ("axes", "button", "label")

#: Types that display text. `label` holds a button's caption and a label's
#: text — the same idea, so it stays one field rather than two.
TEXT_TYPES = ("button", "label")

#: Interactions available on every element type. Universal, not per-type
#: (FR-017a); what varies per type is which single stub is generated.
INTERACTIONS = ("clicked", "hover", "motion", "key")

#: The one stub generated when an element is created (FR-017d).
#:
#: A label is `None`: it displays text and is set from code, so generating a
#: click handler for every one would leave a researcher with a pile of dead
#: functions. Every interaction is still available on a label if they write the
#: handler themselves (FR-017a) — only the automatic stub is withheld.
DEFAULT_INTERACTION = {"axes": "clicked", "button": "clicked", "label": None}

#: Prefix used when auto-suggesting a tag in the designer.
#: `axes` is deliberately abbreviated: `ax` is what a matplotlib user calls the
#: variable, so `ev.ax_0` reads the way their own code already does.
TAG_PREFIX = {"axes": "ax", "button": "button", "label": "label"}

#: Size given to an element placed by a single click rather than a drag, as
#: (width, height) fractions of the window.
#:
#: Fractions scale with the window, so no single pair is ideal at every size;
#: these are chosen so that a maximised window does not produce an absurdly
#: large control. On 1920x1080 a button lands at roughly 134x38 px, a label at
#: 154x32 and a plot at 864x432; on the 800x450 default, 56x16, 64x14 and
#: 360x180.
DEFAULT_SIZE = {
    "axes": (0.45, 0.40),
    "button": (0.07, 0.035),
    "label": (0.08, 0.03),
}

#: Style properties, and which element types carry them.
#:
#: An axes element draws its own appearance through matplotlib, so it takes only
#: `visible`. Everything else applies to the types that render text.
UNIVERSAL_STYLE = ("visible",)
TEXT_STYLE = (
    "background", "text_color", "edge", "edge_width",
    "font", "font_size", "bold", "italic", "align", "enabled",
)

ALIGNMENTS = ("left", "center", "right")

_ROUND = 4


def validate_tag(tag: str, existing=()) -> str:
    """Return `tag` if it is usable, else raise.

    A tag becomes part of a handler's name (`on_clicked_<tag>`) and an attribute
    on `ev`, so an unusable one would produce uncompilable generated code or an
    unreachable element. Checked at entry, never at generation time (FR-005b).
    """
    if not isinstance(tag, str) or not tag:
        raise NameInvalid("A tag is required.")
    if not tag.isidentifier():
        raise NameInvalid(
            f"{tag!r} cannot be used in Python code. Use letters, digits and "
            f"underscores, and do not start with a digit."
        )
    if keyword.iskeyword(tag):
        raise NameInvalid(f"{tag!r} is a Python keyword, so it cannot tag an element.")
    if tag.startswith("_"):
        # Reserved so iterlab can keep its own attributes on `ev` without ever
        # colliding with an element (data-model.md, R10).
        raise NameInvalid(f"{tag!r} starts with an underscore, which iterlab reserves.")
    if tag in existing:
        raise NameInUse(f"Another element is already tagged {tag!r}.")
    return tag


@dataclass(frozen=True)
class Rect:
    """Position and size as fractions of the window, origin bottom-left."""

    left: float
    bottom: float
    width: float
    height: float

    def __post_init__(self):
        for label, value in (
            ("left", self.left),
            ("bottom", self.bottom),
            ("width", self.width),
            ("height", self.height),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{label} must be a number, got {value!r}")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{label} must be within [0, 1], got {value}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be greater than zero")
        if self.left + self.width > 1.0 + 1e-9:
            raise ValueError("element extends past the right edge")
        if self.bottom + self.height > 1.0 + 1e-9:
            raise ValueError("element extends past the top edge")

    def as_list(self):
        return [
            round(float(self.left), _ROUND),
            round(float(self.bottom), _ROUND),
            round(float(self.width), _ROUND),
            round(float(self.height), _ROUND),
        ]

    @classmethod
    def from_list(cls, values):
        if not isinstance(values, (list, tuple)) or len(values) != 4:
            raise ValueError(f"position must be four numbers, got {values!r}")
        return cls(*(float(v) for v in values))


@dataclass(frozen=True)
class Style:
    """How an element looks.

    Every field defaults to `None` or a neutral value meaning "use the theme",
    and only non-defaults are written to the layout file, so a plain element
    stays a two-line entry (Principle II: defaults keep a minimal element terse).

    These are the *starting* values. Researcher code may change any of them at
    run time, and doing so never writes back to the layout file — the layout is
    the initial state, not a live mirror.
    """

    background: str | None = None
    text_color: str | None = None
    edge: str | None = None
    edge_width: int = 0
    font: str | None = None
    font_size: int | None = None
    bold: bool = False
    italic: bool = False
    align: str = "center"
    enabled: bool = True
    visible: bool = True

    def __post_init__(self):
        if self.align not in ALIGNMENTS:
            raise ValueError(f"align must be one of {ALIGNMENTS}, got {self.align!r}")
        if not isinstance(self.edge_width, int) or self.edge_width < 0:
            raise ValueError(f"edge_width must be a non-negative whole number")
        if self.font_size is not None and not (1 <= self.font_size <= 200):
            raise ValueError("font_size must be between 1 and 200")
        for name in ("background", "text_color", "edge"):
            value = getattr(self, name)
            if value is not None and not _is_colour(value):
                raise ValueError(f"{name} must be a colour like '#3366ff', got {value!r}")

    def non_defaults(self) -> dict:
        """Only what differs from the defaults, for a terse layout file."""
        blank = Style()
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) != getattr(blank, f.name)
        }


def _is_colour(value) -> bool:
    """Accept `#rgb`, `#rrggbb`, or a Tk colour name.

    Deliberately permissive about names: Tk knows hundreds, and rejecting one
    it would have accepted is worse than passing it through.
    """
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("#"):
        return len(value) in (4, 7) and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    return value.replace(" ", "").isalpha()


def style_fields_for(element_type: str):
    """Which style properties an element of this type actually has."""
    if element_type in TEXT_TYPES:
        return UNIVERSAL_STYLE + TEXT_STYLE
    return UNIVERSAL_STYLE


@dataclass(frozen=True)
class Element:
    #: The unique identifier within an interface. It is what the researcher's
    #: code sees: `ev.<tag>`, and `on_clicked_<tag>`.
    tag: str
    type: str
    position: Rect
    label: str = ""
    style: Style = field(default_factory=Style)

    def __post_init__(self):
        if self.type not in ELEMENT_TYPES:
            raise ValueError(
                f"unknown element type {self.type!r}; expected one of {ELEMENT_TYPES}"
            )
        if self.type not in TEXT_TYPES and self.label:
            raise ValueError(f"{self.type} elements do not display text")

    @property
    def default_interaction(self):
        """The one interaction that gets a generated stub, or None."""
        return DEFAULT_INTERACTION[self.type]

    @property
    def displays_text(self) -> bool:
        return self.type in TEXT_TYPES

    def handler_name(self, interaction: str) -> str:
        if interaction not in INTERACTIONS:
            raise ValueError(f"unknown interaction {interaction!r}")
        return f"on_{interaction}_{self.tag}"

    def all_handler_names(self):
        """Every handler name this element could have, written or not."""
        return [self.handler_name(i) for i in INTERACTIONS]


@dataclass(frozen=True)
class Window:
    width: int = 800
    height: int = 450

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("window size must be positive")


@dataclass
class Layout:
    """Every element in one interface, in a stable order."""

    window: Window = field(default_factory=Window)
    elements: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @property
    def is_empty(self) -> bool:
        """True when there is nothing to use yet — the editor-mode case (FR-001a)."""
        return not self.elements

    def tags(self):
        return list(self.elements)

    def add(self, element: Element) -> None:
        validate_tag(element.tag, existing=self.elements)
        self.elements[element.tag] = element

    def remove(self, tag: str) -> Element:
        return self.elements.pop(tag)

    def move(self, tag: str, position: Rect) -> None:
        self.elements[tag] = replace(self.elements[tag], position=position)

    def relabel(self, tag: str, label: str) -> None:
        self.elements[tag] = replace(self.elements[tag], label=label)

    def restyle(self, tag: str, **changes) -> None:
        """Change style properties of one element in the layout."""
        element = self.elements[tag]
        allowed = set(style_fields_for(element.type))
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(
                f"{element.type} elements have no style {sorted(unknown)!r}"
            )
        self.elements[tag] = replace(element, style=replace(element.style, **changes))

    def retag(self, old: str, new: str) -> None:
        """Change a tag in the layout only.

        The caller is responsible for the code file, and must rewrite it *first*
        so that a failure leaves the two consistent (R14).
        """
        validate_tag(new, existing=[n for n in self.elements if n != old])
        # Rebuild to preserve insertion order rather than moving the entry to
        # the end, so version-control diffs stay minimal.
        self.elements = {
            (new if t == old else t): (replace(e, tag=new) if t == old else e)
            for t, e in self.elements.items()
        }

    def next_tag(self, element_type: str) -> str:
        """The tag offered when an element is created (FR-005a)."""
        prefix = TAG_PREFIX[element_type]
        index = 0
        while f"{prefix}_{index}" in self.elements:
            index += 1
        return f"{prefix}_{index}"
