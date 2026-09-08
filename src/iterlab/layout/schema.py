"""The layout model, and the rules a layout must satisfy.

No GUI imports. This module is the single source of truth for both the designer
and the runtime (constitution Principle II), which is why it lives outside `ui`.
"""

from __future__ import annotations

import keyword
from dataclasses import dataclass, field, replace

from ..errors import NameInUse, NameInvalid

#: Written into every layout file. Bumped only when the format changes in a way
#: an older build could not read (contracts/layout-schema.md).
SCHEMA_VERSION = 1

#: Element types this build knows. A closed set: an unknown type in a file of a
#: recognized schema version is a defect, not something to skip over.
ELEMENT_TYPES = ("plot_area", "button")

#: Interactions available on every element type. Universal, not per-type
#: (FR-017a); what varies per type is which single stub is generated.
INTERACTIONS = ("clicked", "hover", "motion", "key")

#: The one stub generated when an element is created (FR-017d).
DEFAULT_INTERACTION = {"plot_area": "clicked", "button": "clicked"}

#: Prefix used when auto-suggesting a name in the designer.
NAME_PREFIX = {"plot_area": "plot", "button": "button"}

#: Size given to an element placed by a single click rather than a drag, as
#: (width, height) fractions of the window.
#:
#: Fractions scale with the window, so no single pair is ideal at every size;
#: these are chosen to look right on a maximised window while staying usable on
#: a small one. On 1920x1080 a button lands at roughly 230x65 px and a plot at
#: 864x432; on the 800x450 default, 96x27 and 360x180.
DEFAULT_SIZE = {"plot_area": (0.45, 0.40), "button": (0.12, 0.06)}

_ROUND = 4


def validate_name(name: str, existing=()) -> str:
    """Return `name` if it is usable, else raise.

    A name becomes part of a function name (`on_clicked_<name>`) and an attribute
    on `ev`, so an unusable one would produce uncompilable generated code or an
    unreachable element. Checked at entry, never at generation time (FR-005b).
    """
    if not isinstance(name, str) or not name:
        raise NameInvalid("A name is required.")
    if not name.isidentifier():
        raise NameInvalid(
            f"{name!r} cannot be used in Python code. Use letters, digits and "
            f"underscores, and do not start with a digit."
        )
    if keyword.iskeyword(name):
        raise NameInvalid(f"{name!r} is a Python keyword, so it cannot name an element.")
    if name.startswith("_"):
        # Reserved so iterlab can keep its own attributes on `ev` without ever
        # colliding with an element (data-model.md, R10).
        raise NameInvalid(f"{name!r} starts with an underscore, which iterlab reserves.")
    if name in existing:
        raise NameInUse(f"Another element is already called {name!r}.")
    return name


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
class Element:
    name: str
    type: str
    position: Rect
    label: str = ""

    def __post_init__(self):
        if self.type not in ELEMENT_TYPES:
            raise ValueError(
                f"unknown element type {self.type!r}; expected one of {ELEMENT_TYPES}"
            )
        if self.type != "button" and self.label:
            raise ValueError(f"{self.type} elements do not have a label")

    @property
    def default_interaction(self) -> str:
        return DEFAULT_INTERACTION[self.type]

    def handler_name(self, interaction: str) -> str:
        if interaction not in INTERACTIONS:
            raise ValueError(f"unknown interaction {interaction!r}")
        return f"on_{interaction}_{self.name}"

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

    def names(self):
        return list(self.elements)

    def add(self, element: Element) -> None:
        validate_name(element.name, existing=self.elements)
        self.elements[element.name] = element

    def remove(self, name: str) -> Element:
        return self.elements.pop(name)

    def move(self, name: str, position: Rect) -> None:
        self.elements[name] = replace(self.elements[name], position=position)

    def relabel(self, name: str, label: str) -> None:
        self.elements[name] = replace(self.elements[name], label=label)

    def rename(self, old: str, new: str) -> None:
        """Rename in the layout only.

        The caller is responsible for the code file, and must rewrite it *first*
        so that a failure leaves the two consistent (R14).
        """
        validate_name(new, existing=[n for n in self.elements if n != old])
        # Rebuild to preserve insertion order rather than moving the entry to
        # the end, so version-control diffs stay minimal.
        self.elements = {
            (new if n == old else n): (replace(e, name=new) if n == old else e)
            for n, e in self.elements.items()
        }

    def next_name(self, element_type: str) -> str:
        """The default offered in the creation dialog (FR-005a)."""
        prefix = NAME_PREFIX[element_type]
        index = 0
        while f"{prefix}_{index}" in self.elements:
            index += 1
        return f"{prefix}_{index}"
