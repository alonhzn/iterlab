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
SCHEMA_VERSION = 6

#: Element types this build knows. A closed set: an unknown type in a file of a
#: recognized schema version is a defect, not something to skip over.
ELEMENT_TYPES = (
    "axes", "button", "label", "text_box", "number_box",
    "file_select", "folder_select",
)

#: Types that display text. One field, `label`, holds it for all of them: a
#: button's caption, a label's text, and the contents of a box. They are the
#: same idea — the string the element shows — and in code they are all reached
#: as `.text`.
TEXT_TYPES = (
    "button", "label", "text_box", "number_box",
    "file_select", "folder_select",
)

#: Types that take typed input rather than only displaying text.
INPUT_TYPES = ("text_box", "number_box")

#: Types that open an operating-system dialog and remember what was chosen.
SELECT_TYPES = ("file_select", "folder_select")

#: Types carrying the `extensions` filter. Only the file selector: filtering a
#: folder chooser by file type would mean nothing.
EXTENSION_TYPES = ("file_select",)

#: Interactions available on every element type. Universal, not per-type
#: (FR-017a); what varies per type is which single stub is generated.
#:
#: `changed` is universal in the same sense the rest are: any element may have a
#: handler written for it, and one that never changes simply never fires — the
#: same as an element nobody wrote a handler for. It exists because a box needs
#: an event meaning "the researcher finished entering a value", which is not the
#: same question as "a key went down" and cannot be built out of `key` without
#: every researcher reimplementing the same debounce.
INTERACTIONS = ("clicked", "hover", "motion", "key", "changed")

#: The one stub generated when an element is created (FR-017d).
#:
#: A label is `None`: it is written to rather than interacted with, so a click
#: handler on every one would leave a researcher with a pile of dead functions.
#: Every interaction stays available on any type if they write the handler
#: themselves (FR-017a) — only the automatic stub is withheld.
DEFAULT_INTERACTION = {
    "axes": "clicked",
    "button": "clicked",
    "label": None,
    # On a committed value, not on every keystroke. Redrawing a plot per
    # character is expensive and jumpy, and half-typed input is mostly
    # meaningless - "1" on the way to "100" is a different plot, drawn twice for
    # nothing. `key` is still there for anyone who does want each keystroke.
    "text_box": "changed",
    "number_box": "changed",
    # A selector's stub fires *after* a choice is made, so the generated code
    # can show the path straight away - which is also where the researcher
    # finds out the attribute is called `.path`.
    "file_select": "clicked",
    "folder_select": "clicked",
}

#: Prefix used when auto-suggesting a tag in the designer. Short, and the
#: shorthand a person would use themselves: `ax` for an axes, `cmd` for a command
#: button, `lbl` for a label, `edt` for an edit box, `val` for a numeric one, so
#: `ev.ax_0` reads the way their own matplotlib code already does.
TAG_PREFIX = {
    "axes": "ax",
    "button": "cmd",
    "label": "lbl",
    "text_box": "edt",
    "number_box": "val",
    "file_select": "fileselect",
    "folder_select": "folderselect",
}

#: Types whose first element takes the bare prefix — `fileselect`, not
#: `fileselect_0`. An interface almost always has exactly one of these, and a
#: number on the only one of something is noise the researcher then types into
#: every handler. A second one becomes `fileselect_1`.
BARE_FIRST_TAG = SELECT_TYPES

#: What an element says before anyone has typed anything into it.
#:
#: A new button that says "Click here!" is a working control; one that says
#: `cmd_0` is a placeholder the researcher has to fix before showing anyone.
#: A text box starts empty because anything else would have to be deleted, and
#: a number box starts at zero because a number box with no number in it is not
#: in a valid state.
DEFAULT_TEXT = {
    "button": "Click here!",
    "label": "Information:",
    "text_box": "",
    "number_box": "0",
    "file_select": "Select a File",
    "folder_select": "Select a Folder",
}


def default_text(element_type) -> str:
    return DEFAULT_TEXT.get(element_type, "")

#: Size given to an element placed by a single click rather than a drag, as
#: (width, height) fractions of the window.
#:
#: Fractions scale with the window, so no single pair is ideal at every size;
#: these are chosen so a maximised window does not produce an absurdly large
#: control. On 1920x1080 a button lands at 173x32 px and a plot at 864x432; on
#: the 800x450 default, 72x14 and 360x180.
#:
#: Everything that is a single line of text shares one height, so a row of them
#: lines up without anyone resizing anything. Widths still differ, because a
#: caption's length is the thing that varies: "Select a Folder" needs more room
#: than "Click here!".
LINE_HEIGHT = 0.03

DEFAULT_SIZE = {
    "axes": (0.45, 0.40),
    "button": (0.09, LINE_HEIGHT),
    "label": (0.10, LINE_HEIGHT),
    # The boxes are deliberately taller: a field someone types into wants more
    # room than a caption they only read.
    "text_box": (0.14, 0.04),
    "number_box": (0.07, 0.04),
    "file_select": (0.12, LINE_HEIGHT),
    "folder_select": (0.13, LINE_HEIGHT),
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

#: Properties shown in the editor without opening the "More" drawer, per type,
#: beyond the tag — which every element has and every element shows.
#:
#: "Basic" means what you must decide to have made the element at all. A button
#: needs its caption; an axes needs nothing, since matplotlib decides how it
#: looks. Everything else — position, colour, font, state — is a refinement, and
#: refinements are what the drawer is for.
#:
#: A new element type adds its own here: a slider's range and starting position
#: are basic in exactly this sense, because a slider without them is not yet a
#: slider.
BASIC_PROPERTIES = {
    "axes": (),
    "button": ("label",),
    "label": ("label",),
    "text_box": ("label",),
    "number_box": ("label",),
    # `extensions` is basic in the same sense a slider's range would be: a file
    # selector that shows every file on the disk is not yet the element the
    # researcher meant to draw.
    "file_select": ("label", "extensions"),
    "folder_select": ("label",),
}


def parse_extensions(raw):
    """"txt, .CSV , jpeg" -> ("txt", "csv", "jpeg"). Empty means every file.

    Deliberately forgiving about how they are written: a leading dot, upper
    case and stray spaces are all things a person types, and none of them is a
    mistake worth refusing. Order is kept, duplicates are not.
    """
    if not raw:
        return ()
    seen = []
    for piece in str(raw).replace(";", ",").split(","):
        cleaned = piece.strip().lstrip("*").lstrip(".").strip().lower()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return tuple(seen)


def basic_properties(element_type):
    """Editable properties this type shows before the drawer is opened."""
    return BASIC_PROPERTIES.get(element_type, ())

#: Positions and sizes are held to two decimals — one part in a hundred of the
#: window. Finer than that is noise: it is below what a researcher can place by
#: dragging, below what they can see, and it makes the layout file unreadable
#: and its diffs meaningless. Rounding happens on construction rather than only
#: on save, so what is in memory is what is on disk and a value never changes
#: under a researcher between drawing it and reopening it.
_ROUND = 2

#: The smallest element that still means something after rounding. Anything
#: rounding to zero would be invalid, so a sliver becomes this instead of an
#: error the researcher did not ask for.
_MIN_EXTENT = 0.01


def _snap(value):
    return round(float(value), _ROUND)


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
        self._snap_to_grid()

    def _snap_to_grid(self):
        """Round to two decimals, keeping the rectangle valid.

        Validation runs first, so a genuinely bad rectangle is still rejected
        rather than quietly rounded into something acceptable. What is corrected
        here are only the artefacts rounding itself introduces: a sliver that
        would round away to nothing, and an edge that rounding nudges past the
        window. Neither is a mistake the researcher made.

        Frozen dataclass, so the fields are set the way `dataclasses.replace`
        would - this is the documented way to normalise in __post_init__.
        """
        left, bottom = _snap(self.left), _snap(self.bottom)
        width = max(_snap(self.width), _MIN_EXTENT)
        height = max(_snap(self.height), _MIN_EXTENT)
        # Rounding out and away from the origin can push a right or top edge
        # past 1.0; give the position back rather than shrink what was drawn.
        left = min(left, round(1.0 - width, _ROUND))
        bottom = min(bottom, round(1.0 - height, _ROUND))
        for name, value in (
            ("left", max(left, 0.0)),
            ("bottom", max(bottom, 0.0)),
            ("width", width),
            ("height", height),
        ):
            object.__setattr__(self, name, value)

    def as_list(self):
        return [self.left, self.bottom, self.width, self.height]

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
    #: Comma-separated file extensions a file selector will offer, e.g.
    #: "txt, csv". Empty means every file. Meaningless on any other type, and
    #: rejected there rather than silently ignored.
    extensions: str = ""

    def __post_init__(self):
        if self.type not in ELEMENT_TYPES:
            raise ValueError(
                f"unknown element type {self.type!r}; expected one of {ELEMENT_TYPES}"
            )
        if self.type not in TEXT_TYPES and self.label:
            raise ValueError(f"{self.type} elements do not display text")
        if self.type not in EXTENSION_TYPES and self.extensions:
            raise ValueError(f"{self.type} elements do not filter by extension")

    @property
    def default_interaction(self):
        """The one interaction that gets a generated stub, or None."""
        return DEFAULT_INTERACTION[self.type]

    @property
    def displays_text(self) -> bool:
        return self.type in TEXT_TYPES

    @property
    def filters_files(self) -> bool:
        return self.type in EXTENSION_TYPES

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
    #: Which iterlab last wrote this file. Provenance, not layout: it is read
    #: from the file and never set by hand, because saving always stamps the
    #: version doing the saving. Empty means a build from before this existed.
    iterlab_version: str = ""

    @property
    def is_empty(self) -> bool:
        """True when there is nothing to use yet — the editor-mode case (FR-001a)."""
        return not self.elements

    def resize(self, width: int, height: int) -> bool:
        """Record the interface's size. Returns whether it actually changed.

        The size is part of the layout because it describes the interface, and
        the point of recording it is that reopening an interface gives back the
        one the researcher was working in rather than the default.
        """
        width, height = int(width), int(height)
        if (self.window.width, self.window.height) == (width, height):
            return False
        self.window = Window(width=width, height=height)
        return True

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

    def set_extensions(self, tag: str, extensions: str) -> None:
        """Set which file types a file selector offers."""
        element = self.elements[tag]
        self.elements[tag] = replace(element, extensions=str(extensions or "").strip())

    def next_tag(self, element_type: str) -> str:
        """The tag offered when an element is created (FR-005a).

        Most types number from zero: `cmd_0`, `cmd_1`. A few take the bare
        prefix first, because an interface almost always has exactly one of
        them and `fileselect` reads better than `fileselect_0` in every handler
        that mentions it. The second one is `fileselect_1`, not `_0`, since the
        bare name is already taken.
        """
        prefix = TAG_PREFIX[element_type]
        if element_type in BARE_FIRST_TAG:
            if prefix not in self.elements:
                return prefix
            index = 1
            while f"{prefix}_{index}" in self.elements:
                index += 1
            return f"{prefix}_{index}"

        index = 0
        while f"{prefix}_{index}" in self.elements:
            index += 1
        return f"{prefix}_{index}"
