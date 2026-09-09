"""Appending handler stubs to the researcher's file — additively, always.

Existence is determined by parsing, not by searching for text: reformatting,
comments and decorators must not cause a duplicate (FR-011, research.md R6).

This module only ever *appends*. The single exception to that rule in the whole
project lives in `rename.py`.

No GUI imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ..errors import CodeFileUnparseable
from .templates import CRLF, LF, atomic_write, detect_newline, read_source


def top_level_function_names(source: str, path=None) -> set:
    """Names of every top-level `def` in the file.

    Nested functions and methods are deliberately excluded: a handler must be at
    module level to be reachable by name.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodeFileUnparseable(
            f"{path or 'the code file'} could not be parsed: {exc}"
        ) from exc
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _is_main_guard(node) -> bool:
    """Whether this top-level node is `if __name__ == "__main__":`.

    Matched structurally rather than by text, for the same reason handler
    existence is: a researcher may have written `'__main__'`, added spaces, or
    compared the other way round, and none of that changes what it is.
    """
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    sides = [test.left, test.comparators[0]]
    names = {s.id for s in sides if isinstance(s, ast.Name)}
    values = {s.value for s in sides if isinstance(s, ast.Constant)}
    return "__name__" in names and "__main__" in values


def main_guard_line(source: str, path=None):
    """The 1-based line a trailing `if __name__ ...` block starts on, or None.

    Only a *trailing* guard counts. One in the middle of a file is not the
    launcher this is looking for, and inserting above it would drop the stub
    into the middle of the researcher's code.

    Any comment lines immediately above it are treated as part of it, so an
    explanation stays attached to the block it explains rather than being left
    stranded above a stub.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodeFileUnparseable(
            f"{path or 'the code file'} could not be parsed: {exc}"
        ) from exc
    if not tree.body or not _is_main_guard(tree.body[-1]):
        return None

    line = tree.body[-1].lineno
    lines = source.splitlines()
    while line > 1:
        above = lines[line - 2].strip()
        if above.startswith("#") or not above:
            line -= 1
        else:
            break
    return line


def has_handler(code_path, handler_name: str) -> bool:
    source = read_source(code_path)
    return handler_name in top_level_function_names(source, code_path)


def append_stub(code_path, element, stub_text: str) -> bool:
    """Append `stub_text` unless the handler already exists.

    Returns True when something was written. Raises `CodeFileUnparseable` rather
    than appending blindly: without an AST there is no way to know whether the
    handler is already there, and a duplicate definition would silently shadow
    the researcher's own work.
    """
    if stub_text is None or element.default_interaction is None:
        # A type with no default interaction, such as a label.
        return False

    path = Path(code_path)
    source = read_source(path)
    handler = element.handler_name(element.default_interaction)

    # Parsing wants LF; the file on disk keeps whatever it already had.
    if handler in top_level_function_names(source.replace(CRLF, LF), path):
        return False

    # Match the file's own line endings. Normalizing them would rewrite every
    # line of a Windows-authored file just to add one stub (Principle V).
    newline = detect_newline(source)
    addition = stub_text.replace(LF, newline)

    guard = main_guard_line(source.replace(CRLF, LF), path)
    if guard is not None:
        # Go in above the `if __name__ ...` launcher rather than after it. That
        # block reads as the end of the file, and a stub landing below it would
        # push it further from the bottom with every element drawn.
        lines = source.split(newline)
        before = newline.join(lines[: guard - 1]).rstrip(newline)
        # Both sides are trimmed of the blank lines already around the seam, or
        # the gap would grow by a couple of lines with every element drawn.
        after = newline.join(lines[guard - 1 :]).lstrip(newline)
        body = addition.strip(newline)
        atomic_write(
            path, f"{before}{newline}{newline}{newline}{body}{newline}{newline}{newline}{after}"
        )
        return True

    separator = "" if source.endswith(newline) or not source else newline
    atomic_write(path, source + separator + addition)
    return True
