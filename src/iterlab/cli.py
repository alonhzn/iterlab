"""The single console entry point.

    iterlab <name>

There is no subcommand. Editing and using an interface are two modes of one
program, switched from inside it (constitution Principle I).
"""

from __future__ import annotations

import argparse
import sys

from .errors import IterlabError, LayoutInvalid, LayoutVersionTooNew

EXIT_OK = 0
EXIT_CANNOT_START = 1
EXIT_USAGE = 2
EXIT_NO_TKINTER = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iterlab",
        description=(
            "Open an iterlab interface. Draw it in editor mode, use it in GUI "
            "mode, and switch with the toggle in the top-left corner."
        ),
    )
    parser.add_argument(
        "name",
        help=(
            "The interface name. A bare name, a path, or either file of the "
            "pair (demo, work/demo, demo.yaml, demo.py)."
        ),
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Imported lazily so that --help works, and so a missing tkinter is
    # diagnosed here rather than surfacing as an ImportError at import time.
    from .app import open_interface
    from .ui.app import TkinterMissing

    try:
        open_interface(args.name)
    except TkinterMissing as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NO_TKINTER
    except (LayoutInvalid, LayoutVersionTooNew) as exc:
        print(f"iterlab: {exc}", file=sys.stderr)
        return EXIT_CANNOT_START
    except OSError as exc:
        print(f"iterlab: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except IterlabError as exc:
        print(f"iterlab: {exc}", file=sys.stderr)
        return EXIT_CANNOT_START
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
