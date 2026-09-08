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
from ..runtime.startupcheck import fingerprint as startup_fingerprint
from . import elements as element_factory
from .faultbanner import FaultBanner
from .startupnotice import StartupNotice


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
        self.notice = StartupNotice(
            self.frame, on_rerun=self.rerun_startup, on_restart=app.restart_session
        )
        #: The loader generation this runner has already inspected, so the file
        #: is re-parsed once per edit rather than once per click. None rather
        #: than 0 so the first check always happens: returning from the editor
        #: builds a runner whose loader has not loaded anything yet, and the
        #: file may well have been edited while the editor was open.
        self._checked_generation = None
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
            after_invoke=self._after_invoke,
        )

        self.handles = {}
        self._build_elements()
        self.run_startup()
        # A file edited while the editor was open is an edit like any other.
        self.check_startup_staleness()

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
                if element.type == "axes"
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
            # Recorded from the file rather than from what ran, so that an edit
            # made *while* startup was running is still noticed afterwards.
            self.session.startup_fingerprint = startup_fingerprint(
                self.interface.code_path
            )
            self._checked_generation = self.loader.generation
        self._redraw_plots()
        return ok

    def ensure_startup(self) -> None:
        """Called before each interaction, for the deferred-first-run case."""
        if not self.session.startup_done:
            self.run_startup()

    # -- staleness -------------------------------------------------------

    def check_startup_staleness(self) -> bool:
        """Raise the notice if `on_startup` has changed since it ran.

        Only after a real reload: the generation check means an untouched file
        costs nothing, however many times it is clicked.
        """
        if not self.session.startup_done or self.loader is None:
            return False
        if self.loader.generation == self._checked_generation:
            return self.notice.visible
        self._checked_generation = self.loader.generation

        if startup_fingerprint(self.interface.code_path) == self.session.startup_fingerprint:
            return False
        self.notice.show()
        return True

    def rerun_startup(self) -> bool:
        """Run `on_startup` again over the session that is already there.

        Deliberately *not* a restart. The researcher keeps everything on `ev`,
        which is the point — re-running is worth offering precisely because it
        does not cost the data load that a restart costs.

        The trade is theirs to make, and it is a real one: startup code that
        appends rather than assigns, or opens a connection rather than replacing
        one, will do it twice. `ev.x = load(...)` rebinds and is safe, which is
        the idiom the guide teaches; `ev.log.append(...)` is not. That is why
        this is offered next to a restart rather than done automatically.
        """
        ok = self.dispatcher.invoke("on_startup", args=(self.ev,))
        if ok:
            self.session.startup_done = True
            self.session.startup_fingerprint = startup_fingerprint(
                self.interface.code_path
            )
            self.notice.dismiss()
        self._redraw_plots()
        return ok

    def _after_invoke(self):
        self._redraw_plots()
        self.check_startup_staleness()

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
