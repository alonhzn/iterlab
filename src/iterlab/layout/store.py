"""Reading and writing the layout file.

An interface is two files: the researcher's `demo.py`, and `demo_layout.py`
written by iterlab. The second holds what was drawn *and* the class that lets an
editor complete `ev.` inside a handler - one artifact, generated together, so
the two cannot drift apart.

It is a Python module, and iterlab **never imports it**. The layout is lifted
out of the parse tree and evaluated as literals only. That is the whole reason
this is safe: opening somebody else's interface must not run their file, and an
`import` here would mean exactly that. A computed value in `LAYOUT` is refused
rather than evaluated, which is a small price for the guarantee.

The file format is public surface (contracts/layout-schema.md): changes here are
MAJOR. 2.0.0 replaced YAML with this, and deliberately without a migration -
files written by 1.x do not open.
"""

from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

from ..errors import LayoutInvalid, LayoutVersionTooNew
from .schema import (
    SCHEMA_VERSION,
    Element,
    Layout,
    Rect,
    Style,
    Window,
    style_fields_for,
    validate_tag,
)

_ELEMENT_KEYS = {"type", "position", "label", "style", "extensions"}
_TOP_KEYS = {
    "schema_version", "iterlab_version", "window", "elements", "toolbar_collapsed",
}
_WINDOW_KEYS = {"width", "height"}


def _reject_unknown(mapping, allowed, where):
    """Unknown keys are an error, not something to skip.

    Ignoring them would silently delete them on the next save, which is the
    class of data loss Principle V exists to prevent.
    """
    unknown = set(mapping) - allowed
    if unknown:
        raise LayoutInvalid(
            f"unrecognized {where} {sorted(unknown)!r}; "
            f"expected some of {sorted(allowed)!r}"
        )


#: Migrations from an older schema, keyed by the version they upgrade *from*.
#: Each returns the raw mapping as the next version would have written it.
#:
#: Empty, and correctly so. Schema 8 is the first of this file format: 2.0.0
#: replaced the YAML pair with a Python module and deliberately shipped no
#: migration, so there is no older file this build could be handed. Migrations
#: are written when a change actually happens rather than in advance (FR-036c),
#: and the machinery below stays because the next one will need it.
MIGRATIONS = {}


def _migrate(raw, version, path):
    """Bring `raw` forward to the current schema, one version at a time."""
    started_at = version
    while version < SCHEMA_VERSION:
        migrate = MIGRATIONS.get(version)
        if migrate is None:  # pragma: no cover - guarded by the table above
            raise LayoutInvalid(
                f"{path} uses layout schema {version}, and this build has no way "
                f"to bring it forward to {SCHEMA_VERSION}."
            )
        raw = migrate(raw)
        version = raw["schema_version"]
    return raw, started_at


#: The name the layout is assigned to in the file.
LAYOUT_NAME = "LAYOUT"


def read_layout_literal(source: str, path=None):
    """Lift `LAYOUT` out of the module text without running any of it.

    Parsed, then evaluated as literals only. A file that does something on the
    way past - a print, an environment write, a call of any kind - never gets
    the chance, because nothing here executes. That is what keeps opening
    somebody else's interface as safe as opening a data file.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise LayoutInvalid(f"{path or 'the layout'} could not be parsed: {exc}") from exc

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == LAYOUT_NAME
            for target in node.targets
        ):
            continue
        try:
            return ast.literal_eval(node.value)
        except ValueError as exc:
            raise LayoutInvalid(
                f"{path or 'the layout'} has a {LAYOUT_NAME} that is computed rather "
                f"than written out. It is read without being run, so every value in "
                f"it has to be a literal: {exc}"
            ) from exc

    raise LayoutInvalid(f"{path or 'the layout'} has no {LAYOUT_NAME}.")


def load(path) -> Layout:
    """Read a layout, migrating it forward if it was written by an older build."""
    path = Path(path)
    raw = read_layout_literal(path.read_text(encoding="utf-8"), path)

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise LayoutInvalid(f"{path} should contain a mapping, found {type(raw).__name__}")

    version = raw.get("schema_version")
    if version is None:
        raise LayoutInvalid(f"{path} has no schema_version.")
    if not isinstance(version, int) or isinstance(version, bool):
        raise LayoutInvalid(f"{path} has a non-integer schema_version: {version!r}")
    if version > SCHEMA_VERSION:
        # Refuse rather than partially understand. Opening it and saving it back
        # would discard whatever the newer version recorded (FR-036b).
        raise LayoutVersionTooNew(found=version, supported=SCHEMA_VERSION, path=path)
    migrated_from = None
    if version < SCHEMA_VERSION:
        raw, migrated_from = _migrate(raw, version, path)

    _reject_unknown(raw, _TOP_KEYS, "top-level key")

    window_raw = raw.get("window") or {}
    if not isinstance(window_raw, dict):
        raise LayoutInvalid("window should be a mapping")
    _reject_unknown(window_raw, _WINDOW_KEYS, "window key")
    try:
        window = Window(**window_raw)
    except (TypeError, ValueError) as exc:
        raise LayoutInvalid(f"invalid window: {exc}") from exc

    elements_raw = raw.get("elements") or {}
    if not isinstance(elements_raw, dict):
        raise LayoutInvalid("elements should be a mapping of tag to element")

    stamp = raw.get("iterlab_version") or ""
    layout = Layout(
        window=window,
        elements={},
        schema_version=SCHEMA_VERSION,
        iterlab_version=str(stamp),
        toolbar_collapsed=bool(raw.get("toolbar_collapsed", False)),
    )
    for tag, body in elements_raw.items():
        if not isinstance(body, dict):
            raise LayoutInvalid(f"element {tag!r} should be a mapping")
        _reject_unknown(body, _ELEMENT_KEYS, f"key on element {tag!r}")
        try:
            validate_tag(str(tag), existing=layout.elements)
            element_type = body.get("type")
            element = Element(
                tag=str(tag),
                type=element_type,
                position=Rect.from_list(body.get("position")),
                label=body.get("label", "") or "",
                style=_read_style(body.get("style"), element_type),
                extensions=body.get("extensions", "") or "",
            )
        except Exception as exc:
            raise LayoutInvalid(f"element {tag!r} is invalid: {exc}") from exc
        layout.elements[element.tag] = element
    return layout


def _read_style(raw, element_type) -> Style:
    if raw is None:
        return Style()
    if not isinstance(raw, dict):
        raise LayoutInvalid("style should be a mapping")
    allowed = set(style_fields_for(element_type))
    unknown = set(raw) - allowed
    if unknown:
        raise LayoutInvalid(
            f"{element_type} elements have no style {sorted(unknown)!r}; "
            f"expected some of {sorted(allowed)!r}"
        )
    return Style(**raw)


MODULE = '''"""Written by iterlab. Rewritten whenever you change the interface.

This is your interface: what you drew, and the class that lets your editor
complete `ev.` inside a handler.

iterlab reads this file without importing it - the layout below is lifted out
and evaluated as literals - so every value in it has to be written out rather
than computed.
"""

{typing_block}{layout}


class Ev:
    """Your interface, as your editor sees it."""

{declarations}    # `ev` is yours to fill as well: these keep your own attributes from reading
    # as errors, while the elements above keep their types.
    def __getattr__(self, name: str): ...

    def __setattr__(self, name: str, value) -> None: ...
'''

#: Layout element type -> the name to declare it as, imported from
#: `iterlab.types`. That module imports the widgets, so it cannot be imported
#: here: `test_layout_file` asserts the two lists agree.
TYPE_NAMES = {
    "axes": "Axes",
    "button": "Button",
    "label": "Label",
    "text_box": "TextBox",
    "number_box": "NumberBox",
    "file_select": "FileSelect",
    "folder_select": "FolderSelect",
}

#: An element type this build does not know - a file from a newer iterlab -
#: still gets a declaration, as the base every element shares.
FALLBACK_TYPE = "Element"


#: How wide a line may be before it is broken up. Wide enough that an element
#: fits on one line, which is how anyone reading the file wants to see it.
_WIDTH = 88


def _format(value, indent: int = 0) -> str:
    """A literal, formatted for somebody to read and edit by hand.

    `pprint` produces valid Python but lines it up under the opening brace,
    which puts an element's keys in a different column for every tag. This is
    the shape a person would write: one thing per line, four-space indents, and
    anything that fits left on one line.
    """
    pad = " " * indent
    inner = " " * (indent + 4)

    if isinstance(value, dict):
        if not value:
            return "{}"
        entries = [
            (repr(str(key)), _format(item, indent + 4)) for key, item in value.items()
        ]
        flat = "{" + ", ".join(f"{key}: {item}" for key, item in entries) + "}"
        if indent + len(flat) <= _WIDTH and "\n" not in flat:
            return flat
        lines = "".join(f"{inner}{key}: {item},\n" for key, item in entries)
        return "{\n" + lines + pad + "}"

    if isinstance(value, list):
        items = [_format(item, indent + 4) for item in value]
        flat = "[" + ", ".join(items) + "]"
        if indent + len(flat) <= _WIDTH and "\n" not in flat:
            return flat
        lines = "".join(f"{inner}{item},\n" for item in items)
        return "[\n" + lines + pad + "]"

    return repr(value)


def _type_names(layout: Layout) -> dict:
    return {
        tag: TYPE_NAMES.get(element.type, FALLBACK_TYPE)
        for tag, element in layout.elements.items()
    }


def _typing_block(layout: Layout) -> str:
    """The import an editor follows, and the interpreter never does."""
    used = sorted(set(_type_names(layout).values()))
    if not used:
        return ""
    imported = ", ".join(used)
    return (
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        f"    from iterlab.types import {imported}\n"
        "\n"
    )


def _declarations(layout: Layout) -> str:
    """One line per element: what your editor offers after `ev.`."""
    names = _type_names(layout)
    if not names:
        return "    # Nothing drawn yet.\n\n"
    body = "".join(f'    {tag}: "{names[tag]}"\n' for tag in names)
    return body + "\n"


def _serialize(layout: Layout) -> str:
    from .. import __version__

    body = {
        "schema_version": SCHEMA_VERSION,
        # Always the version doing the writing, never what the file said before:
        # saving *is* this version touching the file.
        "iterlab_version": __version__,
        "window": {"width": layout.window.width, "height": layout.window.height},
        "toolbar_collapsed": layout.toolbar_collapsed,
        "elements": {},
    }
    for tag, element in layout.elements.items():
        entry = {"type": element.type, "position": element.position.as_list()}
        if element.displays_text:
            entry["label"] = element.label
        # Only what differs from the defaults, so a plain element stays terse.
        if element.extensions:
            entry["extensions"] = element.extensions
        style = element.style.non_defaults()
        if style:
            entry["style"] = style
        body["elements"][tag] = entry
    # Insertion order is preserved, so a round trip with no edits produces a
    # byte-identical file and diffs stay minimal.
    literal = _format(body)
    return MODULE.format(
        name=Path(getattr(layout, "_path", "demo")).stem or "demo",
        typing_block=_typing_block(layout),
        layout=f"{LAYOUT_NAME} = {literal}",
        declarations=_declarations(layout),
    )


def save(layout: Layout, path) -> None:
    """Write atomically: temp file in the same directory, then replace.

    `os.replace` is atomic on POSIX and Windows alike. An interruption leaves the
    previous file intact rather than a truncated one (FR-013).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _serialize(layout)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        # Best-effort cleanup; the original file is untouched either way.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def create_empty(path) -> Layout:
    layout = Layout()
    save(layout, path)
    return layout
