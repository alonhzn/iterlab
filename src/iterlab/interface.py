"""An interface: a `.yaml` and a `.py` sharing a basename in one directory.

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
        if path.suffix in (".yaml", ".yml", ".py"):
            path = path.with_suffix("")
        directory = path.parent if str(path.parent) != "" else Path(".")
        return cls(name=path.name, directory=directory.resolve())

    @property
    def layout_path(self) -> Path:
        return self.dir / f"{self.name}.yaml"

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
        self.write_ev_types()

    def write_ev_types(self) -> None:
        """Keep the generated type module level with the elements.

        Here because this is the one place every element change passes through -
        drawing, renaming, deleting - so the module cannot fall behind what is
        on the canvas. It rewrites nothing when the text has not changed, so a
        drag that only moves an element touches no file but the layout.

        Never fatal: completions are a convenience, and a convenience that can
        stop someone saving their layout is not one.
        """
        from .codegen import evtypes

        try:
            evtypes.write(self.code_path, self.layout)
        except OSError:
            pass
