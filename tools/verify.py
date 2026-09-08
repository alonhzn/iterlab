"""Set up a scratch interface for the manual verification pass (Gate 2).

    python tools/verify.py

Builds a throwaway interface with a plot, a label and two buttons, writes
research code that exercises slow loading, plotting, a deliberate fault and a
recoverable typo, then opens it. Everything lands in a temporary directory, so
nothing in your own work is touched.

The point is to remove the setup from the manual pass. VERIFICATION.md lists
what to look at; this puts something in front of you to look at it with.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from iterlab.app import open_interface  # noqa: E402
from iterlab.layout.schema import Rect  # noqa: E402

RESEARCH_CODE = '''import time

import numpy as np


def on_startup(ev):
    # Deliberately slow, so item 6 has something to measure. It must run once
    # per session and never again on an edit.
    time.sleep(1.5)
    ev.x = np.linspace(0, 12, 4000)
    ev.clicks = 0
    ev.spectrum.plot(ev.x, np.sin(ev.x))
    ev.status.text = "loaded once - now edit this file and click Redraw"


def on_clicked_redraw(ev, event):
    ev.clicks += 1
    ev.spectrum.clear()
    # Change the 2 below to 5, save, and click again. The curve must change and
    # the load above must NOT repeat.
    ev.spectrum.plot(ev.x, np.sin(2 * ev.x))
    ev.status.text = f"redrawn {ev.clicks}x with the {event.button} button"


def on_clicked_break_it(ev, event):
    # Item 9: the banner must be genuinely noticeable while you are looking at
    # the plot, not merely present.
    raise ValueError("this failure is intentional - the session must survive")
'''


def main():
    work = Path(tempfile.mkdtemp(prefix="iterlab_verify_"))
    name = "verify"
    print(f"scratch interface: {work / name}.py\n")

    app = open_interface(str(work / name), _show=False)
    designer = app.built
    designer.create_element("plot_area", Rect(0.06, 0.42, 0.88, 0.52), name="spectrum")
    designer.create_element("label", Rect(0.06, 0.33, 0.55, 0.05), name="status")
    designer.create_element("button", Rect(0.06, 0.16, 0.14, 0.07), name="redraw")
    designer.create_element("button", Rect(0.24, 0.16, 0.14, 0.07), name="break_it")
    (work / f"{name}.py").write_text(RESEARCH_CODE, encoding="utf-8")
    designer.select(None)

    print(__doc__.split("The point is")[0].strip())
    print("\nOpen VERIFICATION.md alongside and work through the checklist.")
    print("There is no unwritten handler yet - draw one more button and leave it")
    print("empty to check item 10.\n")
    try:
        app.run()
    finally:
        shutil.rmtree(work, ignore_errors=True)
        print("\nscratch interface removed. Record the result in VERIFICATION.md.")


if __name__ == "__main__":
    main()
