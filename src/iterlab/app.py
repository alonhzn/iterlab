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

    # Every iterlab since 1.4.0 stamps what it writes, so an unstamped layout was
    # written by hand or by some other tool. It still gets copied and announced:
    # it is the one crossing where nothing says what the file was made for.
    if recorded:
        described = f"{interface.name} was last edited by {recorded}"
    else:
        described = f"{interface.name}'s layout does not say which iterlab wrote it"

    if written:
        print(
            f"iterlab: {described}, and this "
            f"is {__version__}. Copies of both files were saved first:"
        )
        for path in written:
            print(f"    {path.name}")
    else:
        # Either the copies were already there from a previous crossing, or they
        # could not be written. Say which, rather than staying silent about a
        # guard that did not run.
        print(
            f"iterlab: {described}, and this "
            f"is {__version__}. No new backups were written (they already exist, "
            f"or the folder is not writable)."
        )
    return written


def _warn_about_a_1x_project(interface) -> bool:
    """Say so when a `.yaml` from 1.x is sitting there, and carry on.

    2.0.0 replaced the YAML layout with a Python module and shipped no
    migration. Without this, opening a 1.x interface looks like opening a brand
    new one - the old file is not read, not deleted, and not mentioned, and the
    researcher is left wondering where their layout went. It is still on disk;
    they just cannot open it with this version.
    """
    from .interface import LEGACY_SUFFIX

    legacy = interface.dir / f"{interface.name}{LEGACY_SUFFIX}"
    if not legacy.exists() or interface.layout_path.exists():
        return False
    print(
        f"iterlab: {legacy.name} was written by iterlab 1.x, which kept the layout"
        f" in YAML.\n"
        f"    2.0.0 keeps it in {interface.layout_path.name} instead, and cannot"
        f" read the old format.\n"
        f"    Your file has not been touched. This opens as a new interface."
    )
    return True


def open_interface(name: str, _show=True, _root=None):
    interface = Interface.resolve(name)
    _warn_about_a_1x_project(interface)
    created = interface.ensure_files()
    interface.load_layout()
    guard_version(interface)

    from .ui.app import App, require_tkinter

    # Matplotlib, now, before the window exists. The editor never draws a plot,
    # so left to itself the import - about a third of a second, and seventy-odd
    # modules - lands on the first switch to the interface, where it reads as
    # iterlab being slow to run what was drawn. Here it is part of opening,
    # which is already a wait. After the tkinter check, so a missing tkinter is
    # still reported as that rather than as an ImportError from matplotlib.
    require_tkinter()
    from .ui import elements  # noqa: F401

    app = App(interface, start_mode=choose_start_mode(interface.layout), root=_root)
    if created:
        # Only now: the size comes from the screen, and nothing below the UI
        # layer is allowed to know there is one.
        app.use_default_window_size()
    app.build(app.mode)
    if _show:  # pragma: no cover - the event loop is display-dependent
        app.run()
    return app
