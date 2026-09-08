"""Loading the researcher's module, and noticing when it changes.

Nothing here ever hands out a stored function object. Callbacks resolve by name
at the moment of invocation, so a reloaded function is picked up with no
rebinding step — the direct correction of the defect that stopped the prior
spike (research.md R2).

No GUI imports.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

UNLOADED = "unloaded"
CURRENT = "current"
BROKEN = "broken"


class NotDefined:
    """Sentinel: no handler of that name exists.

    Distinct from every failure. An element the researcher has not written code
    for is normal, and must never be reported as a fault (FR-028, FR-029).
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<not defined>"

    def __bool__(self):
        return False


NOT_DEFINED = NotDefined()


def stamp(path):
    """(mtime_ns, size). Both, because mtime granularity is coarse on some
    filesystems and a fast edit could otherwise be missed (R2).

    Public because noticing an edited file is not only the loader's business:
    the startup check needs the same question answered without loading anything.
    """
    try:
        st = Path(path).stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def module_name_for(code_path) -> str:
    """The sys.modules key a loader for this file would use."""
    return f"_iterlab_user_{Path(code_path).stem}"


def forget(code_path) -> None:
    """Drop the researcher's module from the import cache.

    Loading already builds a fresh module object every time, so this changes
    nothing for an ordinary reload. It exists for a cold restart, where the
    claim being made is that nothing at all was carried over — and a stale
    entry left in `sys.modules` would make that claim not quite true.
    """
    sys.modules.pop(module_name_for(code_path), None)


class ModuleLoader:
    """Owns one researcher module and its freshness."""

    def __init__(self, code_path, module_name=None):
        self.path = Path(code_path)
        self.module_name = module_name or module_name_for(self.path)
        self.module = None
        self.stamp = None
        self.state = UNLOADED
        self.load_error = None

    # -- freshness -------------------------------------------------------

    def has_changed(self) -> bool:
        return stamp(self.path) != self.stamp

    def refresh(self) -> bool:
        """Load or reload if the file changed. Returns True if it is usable now.

        Skipping the reload when nothing changed is what makes repeated clicks
        between edits cost nothing, and stops module-level code re-running on
        every interaction (FR-026a).
        """
        if self.state == CURRENT and not self.has_changed():
            return True
        return self._load()

    def _load(self) -> bool:
        current = stamp(self.path)
        try:
            spec = importlib.util.spec_from_file_location(self.module_name, self.path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load {self.path}")
            module = importlib.util.module_from_spec(spec)
            # Registered before execution so that dataclasses, pickling and
            # anything else that looks the module up by name behaves normally.
            sys.modules[self.module_name] = module
            spec.loader.exec_module(module)
        except BaseException as exc:
            # Catches SyntaxError, ImportError, and anything raised at module
            # level. BROKEN is never terminal — the next interaction retries,
            # which is what lets a researcher fix a typo and carry on (FR-031).
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            sys.modules.pop(self.module_name, None)
            self.state = BROKEN
            self.load_error = exc
            self.stamp = current
            return False

        self.module = module
        self.stamp = current
        self.state = CURRENT
        self.load_error = None
        return True

    # -- resolution ------------------------------------------------------

    def resolve(self, handler_name: str):
        """Return the current function, or NOT_DEFINED.

        Never returns a stale function: if the module is broken, serving the
        previous version silently would be worse than doing nothing and saying so.
        """
        if self.state != CURRENT or self.module is None:
            return NOT_DEFINED
        try:
            return getattr(self.module, handler_name)
        except AttributeError:
            # The *only* exception getattr raises for a missing name, which is
            # why this branch cannot swallow anything else (research.md R4).
            return NOT_DEFINED
