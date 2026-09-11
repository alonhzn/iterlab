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
#: Written when the change actually happened rather than in advance (FR-036c).
def _migrate_1_to_2(raw):
    """v2 added the per-element `style` block.

    Absent style means every default, which is exactly what a v1 element had,
    so there is nothing to move — only the version to raise. The function
    exists so the path is real and tested rather than assumed.
    """
    raw["schema_version"] = 2
    return raw


def _migrate_2_to_3(raw):
    """v3 renamed the element type `plot_area` to `axes`.

    The handle a researcher reaches through `ev` is now a real matplotlib
    `Axes` rather than an object wrapping one, and the type name follows: what
    it is called in the layout should be what it is. Only the type string moves
    — tags, positions and styles are untouched, so an interface written before
    this keeps working and keeps its names.
    """
    for body in (raw.get("elements") or {}).values():
        if isinstance(body, dict) and body.get("type") == "plot_area":
            body["type"] = "axes"
    raw["schema_version"] = 3
    return raw


def _migrate_3_to_4(raw):
    """v4 added the `text_box` and `number_box` element types.

    Nothing in an existing file changes: every v3 element is still valid, and
    the elements this version adds simply did not appear in one. The version
    still has to move, because the guarantee runs the other way — a file written
    now may contain a type a v3 build has never heard of, and the version gate
    is what makes that build refuse the file cleanly instead of reporting an
    unknown element type as a defect in the researcher's layout.
    """
    raw["schema_version"] = 4
    return raw


def _migrate_4_to_5(raw):
    """v5 added the `file_select` and `folder_select` types, and `extensions`.

    Nothing in an existing file changes - no v4 element had either. As with
    3 -> 4, the version moves so a v4 build refuses a file containing a type it
    has never heard of, instead of reporting it as a defect in the layout.
    """
    raw["schema_version"] = 5
    return raw


def _migrate_5_to_6(raw):
    """v6 records which iterlab last wrote the file.

    An older file simply has no stamp, and an absent stamp already means "some
    build from before this existed" - so there is nothing to fill in. The
    version moves because a v5 build would reject the new key outright.
    """
    raw["schema_version"] = 6
    return raw


def _migrate_6_to_7(raw):
    """v7 records whether the editor's toolbar is collapsed.

    Absent means expanded, which is what every older file means. The version
    moves because a v6 build rejects the new key outright.
    """
    raw["schema_version"] = 7
    return raw


MIGRATIONS = {
    1: _migrate_1_to_2,
    2: _migrate_2_to_3,
    3: _migrate_3_to_4,
    4: _migrate_4_to_5,
    5: _migrate_5_to_6,
    6: _migrate_6_to_7,
}


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
