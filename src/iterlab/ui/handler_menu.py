"""Right-click an element in the editor to go to its code.

    Open in VS Code:            >   (which editor; click to change it)
    ----------------------------
    on_clicked_run_fit    line 42   the element's main handler
    ----------------------------
    on_hover_run_fit       create   everything else it can fire
    on_motion_run_fit      create
    on_key_run_fit        line 57

A handler that exists opens at its line. One that does not is written first,
the way creating an element writes its stub, and then opened - so the menu is
also where a researcher finds out what else an element can do.

Editor mode only. In GUI mode a right-click is the researcher's own: it reaches
their `on_clicked_` handler as `event.button == "right"`.

The heading names the editor: the one chosen, else the one that launched
iterlab, else "<select IDE>". Its submenu lists every editor iterlab knows,
greyed out where it is not installed, and a choice made there is remembered for
every interface and wins over detection from then on.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from ..codegen import inject, templates
from ..errors import CodeFileUnparseable
from ..runtime import editors

UNSELECTED = "<select IDE>"


def heading(editor_id) -> str:
    if editor_id is None:
        return UNSELECTED
    return f"Open in {editors.name_of(editor_id)}:"


def entries(element, code_path):
    """[(interaction, handler name, line or None)], main handler first.

    Raises SyntaxError when the file does not parse: then nobody can say which
    handlers exist, and the menu offers the error's line instead.
    """
    source = templates.read_source(code_path).replace(templates.CRLF, templates.LF)
    lines = editors.handler_lines(source)
    return [
        (interaction, element.handler_name(interaction),
         lines.get(element.handler_name(interaction)))
        for interaction in element.interactions
    ]


def build(designer, tag, parent=None):
    """The menu for one element. Posting it is the caller's business."""
    app = designer.app
    element = designer.layout.elements[tag]
    code_path = Path(designer.interface.code_path)
    current, _how = editors.current()

    menu = tk.Menu(parent or designer.canvas, tearoff=False)
    menu.add_cascade(label=heading(current), menu=_chooser(menu, app, current))
    menu.add_separator()

    try:
        listed = entries(element, code_path)
    except SyntaxError as exc:
        line = exc.lineno or 1
        menu.add_command(
            label=f"{code_path.name} has a syntax error",
            accelerator=f"line {line}",
            command=lambda: go_to(app, code_path, line, f"the syntax error in {code_path.name}"),
        )
        return menu

    for index, (interaction, name, line) in enumerate(listed):
        if index == 1 and element.default_interaction is not None:
            menu.add_separator()  # the main handler above, the optional ones below
        menu.add_command(
            label=name,
            accelerator=f"line {line}" if line else "create",
            command=lambda i=interaction: open_handler(designer, tag, i),
        )
    return menu


def _chooser(parent, app, current):
    menu = tk.Menu(parent, tearoff=False)
    choice = tk.StringVar(menu, value=current or "")
    menu._iterlab_choice = choice  # a Variable is dropped with its last reference
    found = editors.available()
    for editor in editors.EDITORS:
        menu.add_radiobutton(
            label=editor.name if found[editor.id] else f"{editor.name} (not found)",
            value=editor.id,
            variable=choice,
            state="normal" if found[editor.id] else "disabled",
            command=lambda e=editor.id: _choose(app, e),
        )
    menu.add_separator()
    menu.add_radiobutton(
        label="Default text editor (opens the file, not the line)",
        value=editors.DEFAULT_APP,
        variable=choice,
        command=lambda: _choose(app, editors.DEFAULT_APP),
    )
    return menu


def _choose(app, editor_id):
    editors.choose(editor_id)
    app.announce(f"Handlers will open in {editors.name_of(editor_id)}")


def open_handler(designer, tag, interaction):
    """Write the handler if it is not there, then open the file at it."""
    element = designer.layout.elements[tag]
    code_path = Path(designer.interface.code_path)
    name = element.handler_name(interaction)
    try:
        inject.append_stub(
            code_path, element, templates.stub_for(element, interaction), interaction
        )
        listed = entries(element, code_path)
    except (CodeFileUnparseable, SyntaxError) as exc:
        designer.app.announce(f"{code_path.name} does not parse, so {name} was not added: {exc}")
        return None
    line = next((found for _i, n, found in listed if n == name), None) or 1
    return go_to(designer.app, code_path, line, name)


def go_to(app, code_path, line, what):
    """Open the file at `line`, in the editor the menu names."""
    current, _how = editors.current()
    if current is None:
        # Nothing chosen and nothing detected: the file still opens, just not at
        # the line, and the caption says where to look and how to do better.
        current = editors.DEFAULT_APP
    try:
        editors.open_at(current, code_path, line)
    except editors.EditorUnavailable as exc:
        app.announce(str(exc))
        return None
    if current == editors.DEFAULT_APP:
        app.announce(
            f"{what} is at line {line}. Pick an IDE at the top of this menu to go "
            f"straight there"
        )
    else:
        app.announce(f"Opened {what} in {editors.name_of(current)}")
    return line
