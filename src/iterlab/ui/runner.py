"""GUI mode: the interface as drawn, wired to the researcher's code.

Owns the session — the `ev`, the loader, the dispatcher. All three are discarded
when this mode is torn down, which is why a mode switch ends the session
(FR-015d) and switching back begins a fresh one (FR-015e).
"""

from __future__ import annotations

import tkinter as tk

from ..runtime.dispatch import Dispatcher
from ..runtime.environment import Ev
from ..runtime.faults import ConsoleFaultSink, MultiSink
from ..runtime.loader import ModuleLoader
from . import elements as element_factory
from .faultbanner import FaultBanner


class Runner:
    def __init__(self, app, extra_sinks=()):
        self.app = app
        self.interface = app.interface
        self.layout = app.interface.layout

        self.frame = tk.Frame(app.content)
        self.frame.pack(fill="both", expand=True)

        self.banner = FaultBanner(self.frame)
        self.sink = MultiSink(ConsoleFaultSink(), self.banner, *extra_sinks)

        self.ev = Ev()
        self.loader = ModuleLoader(self.interface.code_path)
        self.dispatcher = Dispatcher(
            self.loader,
            self.ev,
            self.sink,
            before_invoke=self.ensure_startup,
            after_invoke=self._redraw_plots,
        )

        # Startup has not run yet. If the code is broken at launch we still open
        # the window (FR-032), and try again on the next interaction (FR-026d).
        self._startup_done = False

        self.handles = {}
        self._build_elements()
        self.run_startup()

    def teardown(self):
        """Drop the session. `ev` and everything in it goes with it."""
        self.ev = None
        self.dispatcher = None
        self.loader = None
        self.handles.clear()

    # -- building --------------------------------------------------------

    def _build_elements(self):
        for element in self.layout.elements.values():
            handle = element_factory.build(self.frame, element, self.dispatcher)
            self.handles[element.tag] = handle
            self.ev._bind_element(element.tag, handle)

    # -- startup ---------------------------------------------------------

    def run_startup(self) -> bool:
        """Run `on_startup` once per session.

        Never re-run once it has succeeded (FR-026e). Retried while it has never
        completed, so a typo in startup cannot strand the session (FR-026d).
        """
        if self._startup_done:
            return True
        ok = self.dispatcher.invoke("on_startup", args=(self.ev,))
        if ok:
            self._startup_done = True
        self._redraw_plots()
        return ok

    def ensure_startup(self) -> None:
        """Called before each interaction, for the deferred-first-run case."""
        if not self._startup_done:
            self.run_startup()

    def _redraw_plots(self):
        """Repaint any plot the researcher's code just changed.

        Calling `ev.spectrum.plot(...)` alters the figure but does not repaint
        the widget. A figure created through `pyplot` would be redrawn
        automatically by matplotlib's stale-callback machinery, but an embedded
        figure has no such hook — and `pyplot` has no place in an embedded app,
        since `plt.show()` would start a second event loop competing with Tk's.
        So the redraw is explicit, exactly as the 2024 designer had to do it.

        `stale` is matplotlib's own record of "something changed since the last
        draw", so an interaction that drew nothing costs a few attribute reads.
        That matters: motion handlers fire continuously.
        """
        for handle in self.handles.values():
            figure = getattr(handle, "figure", None)
            canvas = getattr(handle, "canvas", None)
            if figure is not None and canvas is not None and figure.stale:
                # draw_idle rather than draw: it coalesces, so a handler that
                # draws twenty artists still repaints once.
                canvas.draw_idle()
