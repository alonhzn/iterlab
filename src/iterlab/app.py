"""Opening an interface: resolve the pair, create what is missing, choose a mode.

Kept out of `cli.py` so the library entry point and the console command are
genuinely the same path (contracts/commands.md).
"""

from __future__ import annotations

from .interface import Interface


def choose_start_mode(layout) -> str:
    """Editor when there is nothing to use yet, GUI otherwise (FR-001a).

    A new interface lands where the researcher has to begin anyway; an existing
    one lands ready to use. Neither case asks for a decision up front.
    """
    from .ui.app import EDITOR, GUI

    return EDITOR if layout.is_empty else GUI


def open_interface(name: str, _show=True, _root=None):
    interface = Interface.resolve(name)
    interface.ensure_files()
    interface.load_layout()

    from .ui.app import App

    app = App(interface, start_mode=choose_start_mode(interface.layout), root=_root)
    app.build(app.mode)
    if _show:  # pragma: no cover - the event loop is display-dependent
        app.run()
    return app
