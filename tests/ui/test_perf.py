"""Responsiveness as elements accumulate.

matplotlib-as-toolkit made the 2024 spike slower with every widget added; that
is why every control here is a Tk widget. This is the automated half of the
check — the felt half is item 7 in VERIFICATION.md.
"""

import time

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

TOGGLE_BUDGET_SECONDS = 2.0
CLICK_BUDGET_SECONDS = 0.5


def _grid(designer, count):
    per_row = 5
    for i in range(count):
        row, col = divmod(i, per_row)
        designer.create_element(
            "button",
            Rect(0.02 + col * 0.19, 0.02 + row * 0.19, 0.17, 0.15),
            tag=f"b{i}",
        )


def test_twenty_elements_stay_responsive(make_app):
    app = make_app()
    _grid(app.built, 20)
    assert len(app.interface.layout.tags()) == 20

    app.interface.code_path.write_text(
        "def on_clicked_b0(ev, event):\n    ev.hits = getattr(ev, 'hits', 0) + 1\n",
        encoding="utf-8",
    )

    started = time.perf_counter()
    app.toggle()
    app.root.update()
    toggle_seconds = time.perf_counter() - started
    assert toggle_seconds < TOGGLE_BUDGET_SECONDS, f"mode switch took {toggle_seconds:.2f}s"

    started = time.perf_counter()
    for _ in range(10):
        app.built.handles["b0"].widget.invoke()
    click_seconds = time.perf_counter() - started
    assert click_seconds < CLICK_BUDGET_SECONDS, f"10 clicks took {click_seconds:.2f}s"
    assert app.built.ev.hits == 10
