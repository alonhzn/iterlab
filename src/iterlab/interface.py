"""An interface: `demo.py` and `demo_layout.py` in one directory.

The entire configuration story is "what is it called" (constitution Principle I).
Everything resolves relative to the pair's own directory, never to the working
directory, so moving or launching from elsewhere cannot break an interface
(FR-035).

No GUI imports.
"""

from __future__ import annotations

from pathlib import Path

from .codegen import templates
from .layout import store


#: What the layout file's name adds to the interface's own. It is a Python
#: module, so this has to be importable: a handler says `from demo_layout
#: import Ev`.
LAYOUT_SUFFIX = "_layout"

#: What 1.x called the layout. Looked for only to say something useful when one
#: turns up - 2.0.0 changed the format and does not read them.
LEGACY_SUFFIX = ".yaml"


class Interface:
    def __init__(self, name: str, directory: Path):
        self.name = name
        self.dir = Path(directory)
        self.layout = None

    # -- addressing ------------------------------------------------------

    @classmethod
    def resolve(cls, given: str) -> "Interface":
        """Accept a bare name, a path, or either file of the pair."""
        path = Path(given).expanduser()
        if path.suffix in (".py", ".yaml", ".yml"):
            path = path.with_suffix("")
        # `demo_layout` and `demo_layout.py` both mean the interface `demo`:
        # the layout file is one of the pair, and naming either half should
        # open the same thing.
        if path.name.endswith(LAYOUT_SUFFIX):
            path = path.with_name(path.name[: -len(LAYOUT_SUFFIX)])
        directory = path.parent if str(path.parent) != "" else Path(".")
        return cls(name=path.name, directory=directory.resolve())

    @property
    def layout_path(self) -> Path:
        return self.dir / f"{self.name}{LAYOUT_SUFFIX}.py"

    @property
    def code_path(self) -> Path:
        return self.dir / f"{self.name}.py"

    def exists(self) -> bool:
        return self.layout_path.exists() and self.code_path.exists()

    # -- creation --------------------------------------------------------

    def ensure_files(self) -> bool:
        """Create whatever half of the pair is missing.

        Opening a name that does not exist creates it rather than failing
        (FR-002). An existing code file is never touched.

        Returns whether the *layout* was one of the things created, because a
        brand-new project gets its window size chosen for it and an existing one
        must never have its size touched. The size cannot be decided here: it
        comes from the screen, and this module knows nothing about screens.
        """
        created = not self.layout_path.exists()
        if created:
            store.create_empty(self.layout_path)
        if not self.code_path.exists():
            templates.write_starter_file(self.code_path, self.name)
        return created

    def load_layout(self):
        self.layout = store.load(self.layout_path)
        return self.layout

    def save_layout(self) -> None:
        store.save(self.layout, self.layout_path)

