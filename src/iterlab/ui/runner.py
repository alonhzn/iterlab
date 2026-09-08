"""GUI mode: the interface as drawn, wired to the researcher's code.

Owns the session — the `ev`, the loader, the dispatcher. All three are discarded
when this mode is torn down, which is why a mode switch ends the session
(FR-015d) and switching back begins a fresh one (FR-015e).
"""

from __future__ import annotations

import tkinter as tk

from ..runtime.dispatch import Dispatcher
from ..runtime.faults import ConsoleFaultSink, MultiSink
from ..runtime.loader import ModuleLoader
from . import elements as element_factory
from .faultbanner import FaultBanner


class Runner:
    def __init__(self, app, extra_sinks=()):
        self.app = app
        self.interface = app.interface
        self.layout = app.interface.layout
        #: Owned by the App, not by this mode: it outlives every toggle.
        self.session = app.session

        self.frame = tk.Frame(app.content)
        self.frame.pack(fill="both", expand=True)

        self.banner = FaultBanner(self.frame)
        self.sink = MultiSink(ConsoleFaultSink(), self.banner, *extra_sinks)

        # Elements deleted while in the editor leave nothing behind.
        self.session.reconcile(self.layout.tags())
        self.ev = self.session.ev
        self.loader = ModuleLoader(self.interface.code_path)
        self.dispatcher = Dispatcher(
            self.loader,
            self.ev,
            self.sink,
            before_invoke=self.ensure_startup,
            after_invoke=self._redraw_plots,
        )

        self.handles = {}
        self._build_elements()
        self.run_startup()

    def teardown(self):
        """Drop the widgets. The session — `ev`, figures, startup — survives.

        Element handles point at widgets that are about to be destroyed, so they
        are unbound; the researcher's own data on `ev` is untouched.
        """
        for handle in self.handles.values():
            disconnect = getattr(handle, "disconnect", None)
            if disconnect is not None:
                disconnect()
        self.ev._unbind_elements()
        self.handles.clear()
        self.dispatcher = None
        self.loader = None

    # -- building --------------------------------------------------------

    def _build_elements(self):
        for element in self.layout.elements.values():
            figure = (
                self.session.figure_for(element.tag)
                if element.type == "plot_area"
                else None
            )
            handle = element_factory.build(
                self.frame, element, self.dispatcher, figure=figure
            )
            self.handles[element.tag] = handle
            self.ev._bind_element(element.tag, handle)

    # -- startup ---------------------------------------------------------

    def run_startup(self) -> bool:
        """Run `on_startup` once per session.

        Once per *session*, not once per visit to GUI mode: toggling into the
        editor and back no longer re-runs it, because the session survives.
        Still retried while it has never completed, so a typo in startup cannot
        strand things (FR-026d). `Session.restart()` is how it runs again.
        """
        if self.session.startup_done:
            return True
        ok = self.dispatcher.invoke("on_startup", args=(self.ev,))
        if ok:
            self.session.startup_done = True
        self._redraw_plots()
        return ok

    def ensure_startup(self) -> None:
        """Called before each interaction, for the deferred-first-run case."""
        if not self.session.startup_done:
            self.run_startup()

    def redraw_plots(self):
        return self._redraw_plots()

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
