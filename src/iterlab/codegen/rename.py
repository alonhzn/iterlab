"""Renaming an element's handlers.

**This is the only module in iterlab permitted to modify a line the researcher
wrote** (constitution Principle V). Everything it does is therefore as narrow as
the requirement allows.

The rewrite is driven by AST node positions, never by text substitution. That is
not a style preference — substituting the old name as text would also rewrite:

  * a comment or docstring mentioning it,
  * a string literal containing it,
  * a local variable that happens to share the name,
  * and, worst, a handler belonging to a *different* element whose name merely
    starts with the old one, silently unwiring that element.

Only identifiers at known top-level `FunctionDef` positions are touched
(research.md R14).

No GUI imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ..errors import CodeFileUnparseable
from ..layout.schema import INTERACTIONS
from .templates import CRLF, LF, atomic_write, read_source


def handler_names_for(tag: str) -> set:
    """Every handler name that element could have, written or not."""
    return {f"on_{interaction}_{tag}" for interaction in INTERACTIONS}


def _renamed(old_handler: str, old_name: str, new_name: str) -> str:
    # old_handler is known to be exactly on_<interaction>_<old_name>, so slicing
    # off the suffix is exact — no substring risk.
    return old_handler[: -len(old_name)] + new_name


def rename_handlers(code_path, old_name: str, new_name: str) -> list:
    """Rename this element's handlers in place. Returns the names changed.

    Raises `CodeFileUnparseable` and writes nothing if the file will not parse:
    without an AST there is no way to distinguish a definition from an
    incidental mention, and guessing would put the researcher's work at risk —
    which is what this exception to Principle V exists to avoid, not to create.
    """
    path = Path(code_path)
    if not path.exists():
        return []

    source = read_source(path)
    try:
        # Parsing wants LF; the file keeps whatever line endings it had.
        tree = ast.parse(source.replace(CRLF, LF))
    except SyntaxError as exc:
        raise CodeFileUnparseable(
            f"{path} could not be parsed, so renaming would not be safe: {exc}"
        ) from exc

    wanted = handler_names_for(old_name)
    targets = [
        node
        for node in tree.body  # top level only: a nested def is not a handler
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in wanted
    ]
    if not targets:
        return []

    lines = source.splitlines(keepends=True)
    changed = []

    for node in targets:
        new_handler = _renamed(node.name, old_name, new_name)
        index = node.lineno - 1
        line = lines[index]

        # The name sits immediately after "def " (or "async def ") on the
        # definition line. Locate it by column rather than by searching, so
        # nothing else on the line can be hit.
        keyword = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        start = line.index(keyword, node.col_offset) + len(keyword)
        end = start + len(node.name)
        assert line[start:end] == node.name, "AST position did not match the source"

        lines[index] = line[:start] + new_handler + line[end:]
        changed.append(node.name)

    atomic_write(path, "".join(lines))
    return changed
