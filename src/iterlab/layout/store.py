"""Reading and writing layout files.

The file format is public surface (contracts/layout-schema.md): a layout written
by any version must open in every later version, so changes here are MAJOR.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

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

_ELEMENT_KEYS = {"type", "position", "label", "style"}
_TOP_KEYS = {"schema_version", "window", "elements"}
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
#: Written when the change actually happened rather than in advance (FR-036c).
def _migrate_1_to_2(raw):
    """v2 added the per-element `style` block.

    Absent style means every default, which is exactly what a v1 element had,
    so there is nothing to move — only the version to raise. The function
    exists so the path is real and tested rather than assumed.
    """
    raw["schema_version"] = 2
    return raw


MIGRATIONS = {1: _migrate_1_to_2}


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


def load(path) -> Layout:
    """Read a layout, migrating it forward if it was written by an older build."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LayoutInvalid(f"{path} is not valid YAML: {exc}") from exc

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

    layout = Layout(window=window, elements={}, schema_version=SCHEMA_VERSION)
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


def _serialize(layout: Layout) -> str:
    body = {
        "schema_version": SCHEMA_VERSION,
        "window": {"width": layout.window.width, "height": layout.window.height},
        "elements": {},
    }
    for tag, element in layout.elements.items():
        entry = {"type": element.type, "position": element.position.as_list()}
        if element.displays_text:
            entry["label"] = element.label
        # Only what differs from the defaults, so a plain element stays terse.
        style = element.style.non_defaults()
        if style:
            entry["style"] = style
        body["elements"][tag] = entry
    # sort_keys=False preserves insertion order, so a round trip with no edits
    # produces a byte-identical file and diffs stay minimal.
    return yaml.safe_dump(body, sort_keys=False, allow_unicode=True, default_flow_style=None)


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
