"""A real downgrade: a project made by this iterlab, opened by an older release.

Every test of the version guard simulates the stamp inside one installed
iterlab. This runs the actual crossing between two installed versions, which is
the case the guard exists for: the older build meets a file it did not write,
and has to copy both files aside before touching either.

Run in two steps, with a different iterlab installed for each:

    pip install -e .                  ->  python tools/check_downgrade.py make work
    pip install iterlab==<older>      ->  python tools/check_downgrade.py open work

`open` needs a display (CI runs it under xvfb). It uses only what every release
since the guard shipped has had, since it runs against the older one.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

RECORD = "made_by.json"


def make(directory: Path) -> None:
    """Create a project with the iterlab installed now, drawn and saved."""
    import iterlab
    from iterlab.interface import Interface
    from iterlab.layout.schema import Element, Rect

    directory.mkdir(parents=True, exist_ok=True)
    interface = Interface(name="demo", directory=directory)
    interface.ensure_files()
    interface.load_layout()
    interface.layout.add(Element("go", "button", Rect(0.1, 0.1, 0.3, 0.2), label="Go"))
    interface.save_layout()
    (directory / RECORD).write_text(json.dumps({"version": iterlab.__version__}))
    print(f"made {interface.layout_path} with iterlab {iterlab.__version__}")


def open_with_older(directory: Path) -> int:
    """Open it with the iterlab installed now, which must be older."""
    import iterlab
    from iterlab.app import open_interface

    newer = json.loads((directory / RECORD).read_text())["version"]
    older = iterlab.__version__
    if older == newer:
        print(f"both steps ran iterlab {older}: nothing was crossed")
        return 1

    layout = (directory / "demo_layout.py").read_text(encoding="utf-8")
    code = (directory / "demo.py").read_text(encoding="utf-8")

    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        app = open_interface(str(directory / "demo"), _show=False)
        app.root.update()
        app.root.destroy()
    message = printed.getvalue()
    print(message, end="")

    failures = []
    for name, original in (("demo_layout.py", layout), ("demo.py", code)):
        backup = directory / f"{name}.v{newer}.bak"
        if not backup.exists():
            failures.append(f"no {backup.name}")
        elif backup.read_text(encoding="utf-8") != original:
            failures.append(f"{backup.name} is not the file {newer} left")
    if newer not in message:
        failures.append(f"the message does not name {newer}, the version that wrote it")

    for failure in failures:
        print(f"FAIL: {failure}")
    if not failures:
        print(f"ok: iterlab {older} opened a project from {newer} and backed it up first")
    return 1 if failures else 0


def main(argv) -> int:
    if len(argv) != 3 or argv[1] not in ("make", "open"):
        print(__doc__)
        return 2
    directory = Path(argv[2]).resolve()
    if argv[1] == "make":
        make(directory)
        return 0
    return open_with_older(directory)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
