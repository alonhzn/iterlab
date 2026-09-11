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


def guard_version(interface) -> list:
    """Copy the pair aside if a different iterlab last wrote it.

    Called after loading and before the App exists, which is the only moment
    both files are still exactly as the other version left them: from here on
    the layout can be re-saved by a resize, a migration or any edit.
    """
    from . import __version__, versionguard

    recorded, written = versionguard.guard(interface, __version__)
    if not versionguard.needs_backup(recorded, __version__):
        return written

    # An unstamped file is the commonest crossing of all - every project made
    # before this feature existed - so it must not be the one case that happens
    # in silence.
    described = recorded if recorded else "a build older than 1.4.0"

    if written:
        print(
            f"iterlab: {interface.name} was last edited by {described}, and this "
            f"is {__version__}. Copies of both files were saved first:"
        )
        for path in written:
            print(f"    {path.name}")
    else:
        # Either the copies were already there from a previous crossing, or they
        # could not be written. Say which, rather than staying silent about a
        # guard that did not run.
        print(
            f"iterlab: {interface.name} was last edited by {described}, and this "
            f"is {__version__}. No new backups were written (they already exist, "
            f"or the folder is not writable)."
        )
    return written


def open_interface(name: str, _show=True, _root=None):
    interface = Interface.resolve(name)
    interface.ensure_files()
    interface.load_layout()
    guard_version(interface)

    from .ui.app import App

    app = App(interface, start_mode=choose_start_mode(interface.layout), root=_root)
    app.build(app.mode)
    if _show:  # pragma: no cover - the event loop is display-dependent
        app.run()
    return app
