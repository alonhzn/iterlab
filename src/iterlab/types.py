"""The names a generated type stub points at, so an editor can follow them.

A researcher's handlers take `ev`, and every element on it is attached at run
time from the layout. Nothing static can know that `ev.ax_0` is an axes - so
iterlab writes a small module beside the pair declaring it, and that module
imports the classes from here.

This exists to be a *stable* place to import from. The classes themselves live
in `ui.elements` next to the widgets they drive, which is where they belong and
not where anyone should have to import them from.

Nothing here is needed at run time. The generated module is imported under
`TYPE_CHECKING`, so importing this costs a researcher nothing - but it is a
real module rather than a stub file, so a checker that cannot find stubs still
finds these.
"""

from __future__ import annotations

from .runtime.dispatch import Event
from .ui.elements import (
    AxesHandle,
    ButtonHandle,
    ElementHandle,
    FileSelectHandle,
    FolderSelectHandle,
    LabelHandle,
    NumberBoxHandle,
    TextBoxHandle,
)

#: An axes *is* a matplotlib `Axes` - not a wrapper around one - so every call
#: a researcher already knows resolves to matplotlib's own signature, with
#: `.visible` on top of it.
Axes = AxesHandle
Button = ButtonHandle
Label = LabelHandle
TextBox = TextBoxHandle
NumberBox = NumberBoxHandle
FileSelect = FileSelectHandle
FolderSelect = FolderSelectHandle

#: The base every element type shares: `.tag`, `.visible`, and the style
#: properties. Used for an element type a generated stub does not recognize,
#: which is what an older iterlab meeting a newer layout would hit.
Element = ElementHandle

#: What arrives as the second argument of every handler.
Event = Event

__all__ = [
    "Axes", "Button", "Label", "TextBox", "NumberBox",
    "FileSelect", "FolderSelect", "Element", "Event",
]
