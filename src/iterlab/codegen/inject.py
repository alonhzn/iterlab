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
    separator = "" if source.endswith(newline) or not source else newline
    atomic_write(path, source + separator + addition)
    return True
