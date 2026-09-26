"""Loading the researcher's module, and noticing when it changes.

Nothing here ever hands out a stored function object. Callbacks resolve by name
at the moment of invocation, so a reloaded function is picked up with no
rebinding step — the direct correction of the defect that stopped the prior
spike (research.md R2).

No GUI imports.
"""

from __future__ import annotations

import hashlib
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
    """(mtime_ns, size, content digest) - what "this file changed" means.

    Time and size alone were not enough. Windows records file times in ticks
    of up to about 15 ms, so two same-size saves inside one tick stat
    identically and the second edit was never noticed - `2` changed to `5`
    would keep running as `2`. No person saves that fast; an editor that
    formats on save, or an assistant editing the file, does. The digest makes
    detection exact, for the price of reading a small file on each check.

    Time is kept in the tuple so a save with unchanged content still counts as
    a change, exactly as it always has.

    Public because noticing an edited file is not only the loader's business:
    the startup check needs the same question answered without loading anything.
    """
    try:
        path = Path(path)
        st = path.stat()
        digest = hashlib.blake2b(path.read_bytes(), digest_size=16).digest()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size, digest)


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


def ensure_importable(directory) -> None:
    """Put the project folder first on `sys.path`, as `python demo.py` would.

    Launched from an IDE, Python puts the script's folder on the path itself,
    so `import helper` beside `demo.py` just works. Launched as `iterlab demo`
    it does not: the path starts at the console script, and the same import
    fails with ModuleNotFoundError. The same file must behave the same however
    it was opened, so iterlab supplies what the IDE path gets for free - first,
    because that is where Python puts it.
    """
    folder = str(Path(directory).resolve())
    if folder not in sys.path:
        sys.path.insert(0, folder)


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def forget_project_modules(directory) -> list:
    """Drop every module loaded from the project's own folder. Returns their names.

    `forget` alone leaves a researcher's *helper* modules cached: `demo.py` runs
    `import helper` again, finds `helper` already in `sys.modules`, and gets the
    old code - so an edited helper survived a Hard reset untouched, while the
    button promises a restart "as if freshly launched".

    What must never be forgotten, even when it sits inside the project folder:

    * installed packages. A project's own `.venv` usually lives in the folder,
      and making Python re-import numpy or matplotlib over live C extensions is
      a crash, not a restart;
    * the interpreter's own standard library;
    * iterlab itself, which is running this.
    """
    root = Path(directory).resolve()
    protected = {
        Path(prefix).resolve()
        for prefix in (sys.prefix, sys.base_prefix, sys.exec_prefix)
        if prefix
    }
    protected.add(Path(__file__).resolve().parents[1])

    forgotten = []
    for name, module in list(sys.modules.items()):
        location = getattr(module, "__file__", None)
        if not location:
            continue
        try:
            path = Path(location).resolve()
        except (OSError, ValueError):
            continue
        if "site-packages" in path.parts or "dist-packages" in path.parts:
            continue
        if any(_within(path, guarded) for guarded in protected):
            continue
        if _within(path, root):
            sys.modules.pop(name, None)
            forgotten.append(name)
            _drop_bytecode(module)
    return forgotten


def _drop_bytecode(module) -> None:
    """Delete a forgotten module's compiled cache, so it recompiles from source.

    Taking a helper out of `sys.modules` is not enough on its own: the next
    `import` reads `__pycache__/helper.cpython-*.pyc`, which Python judges
    fresh by whole-second modification time and size - so a same-size edit
    made within a second would come back as the old code. Only a compiled
    cache is removed, which Python writes again on the next import.
    """
    cached = getattr(module, "__cached__", None)
    if not cached:
        return
    try:
        Path(cached).unlink()
    except OSError:
        pass


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
        ensure_importable(self.path.parent)
        # A helper file created since the last load has to be findable. Python
        # caches directory listings for imports, and a new file can miss them.
        importlib.invalidate_caches()
        try:
            spec = importlib.util.spec_from_file_location(self.module_name, self.path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load {self.path}")
            module = importlib.util.module_from_spec(spec)
            # Registered before execution so that dataclasses, pickling and
            # anything else that looks the module up by name behaves normally.
            sys.modules[self.module_name] = module
            exec(self._compile(), module.__dict__)
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

    def _compile(self):
        """The file's code, compiled from its source - never from a cache.

        Python's own import would reuse `__pycache__/demo.cpython-*.pyc` when
        the source's modification time *in whole seconds* and its size both
        match. A same-size edit saved within the same second - `2` changed to
        `5`, the guide's own first example - passes that check, and the old
        code runs with no error anywhere. A person rarely saves twice in one
        second; an editor that formats on save, or an assistant editing the
        file, does it routinely. Noticing the edit is this module's whole job,
        so it does not hand the final say to a cache that cannot see one.

        Bytes, not text, so an encoding declaration or a BOM is honoured the
        way Python honours it. `dont_inherit`, so this module's own
        `from __future__` imports cannot leak into the researcher's.
        """
        return compile(self.path.read_bytes(), str(self.path), "exec", dont_inherit=True)

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
