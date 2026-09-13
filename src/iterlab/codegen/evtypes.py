"""The generated module that tells an editor what `ev` holds.

A handler takes `ev`, and every element on it is attached at run time from the
layout. Nothing static can know that `ev.ax_0` is an axes, so `ev.ax_0.plot(...)`
offers no completion and no signature - the single most useful thing an editor
could tell a researcher about their own interface.

So iterlab writes `<name>_ev.py` beside the pair:

    from iterlab.types import Axes, Button

    class Ev:
        ax_0: Axes
        cmd_0: Button
        def __getattr__(self, name: str): ...
        def __setattr__(self, name: str, value) -> None: ...

and the handlers it generates are annotated `ev: "Ev"`. That is ordinary typing,
so it works in any editor and with any checker rather than in one of them.

The two dunders are not decoration. `ev` is also where a researcher keeps their
own data, and without `__getattr__` every `ev.my_cache` is an error; without
`__setattr__` every `ev.my_cache = ...` is. Both were found by running a checker
over the result rather than by thinking about it.

This file is iterlab's, not the researcher's: it is rewritten whenever the
elements change, and says so at the top. No GUI imports.
"""

from __future__ import annotations

from pathlib import Path

from ..layout.schema import ELEMENT_TYPES
from .templates import LF, atomic_write, detect_newline, read_source

#: Layout element type -> the name to import from `iterlab.types`.
#:
#: Kept here rather than beside those classes because that module imports the
#: widgets, and nothing in codegen may import a GUI module. `test_ev_types`
#: asserts the two agree, so the split cannot drift.
TYPE_NAMES = {
    "axes": "Axes",
    "button": "Button",
    "label": "Label",
    "text_box": "TextBox",
    "number_box": "NumberBox",
    "file_select": "FileSelect",
    "folder_select": "FolderSelect",
}

#: An element type this build does not know - a layout written by a newer
#: iterlab - is still declared, as the base every element shares. Better a
#: known-incomplete answer than a missing attribute.
FALLBACK_TYPE = "Element"

HEADER = '''"""Written by iterlab. Do not edit - it is rewritten when elements change.

This is what lets your editor complete `ev.{example}` and show you what it
offers. It is imported only by type checkers, never at run time, and deleting
it costs you nothing but the completions.
"""

from iterlab.types import {imports}


class Ev:
    """Your interface, as your editor sees it."""

'''

FOOTER = '''
    # `ev` is yours to fill: these keep your own attributes from reading as
    # errors, while the elements above keep their types.
    def __getattr__(self, name: str): ...

    def __setattr__(self, name: str, value) -> None: ...
'''

EMPTY_BODY = "    # No elements drawn yet.\n"


def module_name_for(code_path) -> str:
    """`demo.py` -> `demo_ev`, the name a handler imports `Ev` from."""
    return f"{Path(code_path).stem}_ev"


def path_for(code_path) -> Path:
    """Where the generated module sits: beside the pair it describes."""
    path = Path(code_path)
    return path.with_name(f"{module_name_for(path)}.py")


def render(layout) -> str:
    """The module text for this layout."""
    elements = list(layout.elements.values())
    names = {
        element.tag: TYPE_NAMES.get(element.type, FALLBACK_TYPE)
        for element in elements
    }
    imports = sorted(set(names.values())) or [FALLBACK_TYPE]

    body = "".join(f"    {tag}: {names[tag]}\n" for tag in names) or EMPTY_BODY
    example = next(iter(names), "ax_0")
    header = HEADER.format(example=example, imports=", ".join(imports))
    return header + body + FOOTER


def write(code_path, layout) -> Path:
    """Write the module for this layout, and return where it went.

    Rewritten in full every time: it holds nothing anybody else wrote, so there
    is nothing to preserve and no reason to merge. Untouched when the text has
    not changed, so an editor does not see a file change on every save.
    """
    target = path_for(code_path)
    text = render(layout)

    if target.exists():
        current = read_source(target)
        newline = detect_newline(current)
        if current.replace(newline, LF) == text:
            return target
    else:
        newline = LF

    atomic_write(target, text.replace(LF, newline) if newline != LF else text)
    return target


def matches_element_types() -> bool:
    """Whether every element type this build knows has a name to be declared as.

    Called by the test rather than by the application: a type missing from the
    map is a silent gap - that element would be declared as the base class and
    lose its own completions, with nothing to say so.
    """
    return set(TYPE_NAMES) == set(ELEMENT_TYPES)
