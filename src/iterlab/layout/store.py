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
from .schema import SCHEMA_VERSION, Element, Layout, Rect, Window, validate_name

_ELEMENT_KEYS = {"type", "position", "label"}
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


def load(path) -> Layout:
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
    if version < SCHEMA_VERSION:
        # Unreachable at schema 1: there is no older version. Migration is
        # deliberately unbuilt until there is a real change to migrate (FR-036c).
        raise AssertionError(
            f"no migration exists from layout schema {version} to {SCHEMA_VERSION}"
        )

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
        raise LayoutInvalid("elements should be a mapping of name to element")

    layout = Layout(window=window, elements={}, schema_version=SCHEMA_VERSION)
    for name, body in elements_raw.items():
        if not isinstance(body, dict):
            raise LayoutInvalid(f"element {name!r} should be a mapping")
        _reject_unknown(body, _ELEMENT_KEYS, f"key on element {name!r}")
        try:
            validate_name(str(name), existing=layout.elements)
            element = Element(
                name=str(name),
                type=body.get("type"),
                position=Rect.from_list(body.get("position")),
                label=body.get("label", "") or "",
            )
        except Exception as exc:
            raise LayoutInvalid(f"element {name!r} is invalid: {exc}") from exc
        layout.elements[element.name] = element
    return layout


def _serialize(layout: Layout) -> str:
    body = {
        "schema_version": SCHEMA_VERSION,
        "window": {"width": layout.window.width, "height": layout.window.height},
        "elements": {},
    }
    for name, element in layout.elements.items():
        entry = {"type": element.type, "position": element.position.as_list()}
        if element.type == "button":
            entry["label"] = element.label
        body["elements"][name] = entry
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
