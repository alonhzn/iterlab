"""GUI mode: the interface as drawn, wired to the researcher's code.

Owns the session — the `ev`, the loader, the dispatcher. All three are discarded
when this mode is torn down, which is why a mode switch ends the session
(FR-015d) and switching back begins a fresh one (FR-015e).
"""

from __future__ import annotations

import tkinter as tk

from ..runtime.dispatch import Dispatcher
from ..runtime.faults import ConsoleFaultSink, MultiSink
from ..runtime.loader import ModuleLoader, stamp as file_stamp
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
            self.frame, on_rerun=self.rerun_startup, on_restart=app.restart_app
        )
        #: (mtime, size) of the code file the last time startup staleness was
        #: judged, so the file is parsed once per edit rather than once per
        #: check. None so the first check always happens.
        self._checked_stamp = None
        self._poll_id = None
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
        self._schedule_poll()

    def teardown(self):
        """Drop the widgets. The session — `ev`, figures, startup — survives.

        Element handles point at widgets that are about to be destroyed, so they
        are unbound; the researcher's own data on `ev` is untouched.
        """
        # Capture how each element looks before its widgets go, so the rebuild
        # can put it back. Without this a mode switch silently reverts anything
        # the running interface did - text typed into a box, a colour a handler
        # chose - to whatever the layout file happens to say.
        for tag, handle in self.handles.items():
            element = self.layout.elements.get(tag)
            capture = getattr(handle, "_presentation", None)
            if element is not None and capture is not None:
                self.session.remember(tag, element, capture())

        for handle in self.handles.values():
            disconnect = getattr(handle, "disconnect", None)
            if disconnect is not None:
                disconnect()
        if self._poll_id is not None:
            try:
                self.frame.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
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
                self.frame, element, self.dispatcher, figure=figure,
                # Selectors remember per interface, and the memory lives outside
                # the project folder, so they need to know which one they are in.
                interface_path=self.interface.layout_path,
            )
            state = self.session.presentation_for(element.tag, element)
            restore = getattr(handle, "_restore", None)
            if state and restore is not None:
                restore(state)
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
            self._checked_stamp = file_stamp(self.interface.code_path)
            self._notify_stale(False)
        self._redraw_plots()
        return ok

    def ensure_startup(self) -> None:
        """Called before *every* interaction, whatever it goes on to do.

        The staleness check lives here rather than in the after-hook because the
        after-hook only fires when a handler actually ran. An element with no
        handler written for it is normal, not an error — so a researcher who
        drew a button, wrote nothing for it, and edited `on_startup` would have
        clicked and been told nothing at all.
        """
        if not self.session.startup_done:
            self.run_startup()
        self.check_startup_staleness()

    # -- staleness -------------------------------------------------------

    def check_startup_staleness(self) -> bool:
        """Raise the notice if `on_startup` has changed since it ran.

        Judged from the **file**, not from the loaded module. That matters for
        two reasons. The module is only reloaded when an interaction reaches a
        handler that exists, so anything keyed to loading would miss an edit
        made by a researcher whose element has no handler yet — which is the
        normal state of a freshly drawn element. And reading the file costs
        nothing a researcher can feel, where reloading the module would re-run
        its top-level code on a timer, uninvited.

        The stamp gate means an untouched file is a single `stat` per check.
        """
        if not self.session.startup_done:
            return False
        current = file_stamp(self.interface.code_path)
        if current == self._checked_stamp:
            return self.notice.visible
        self._checked_stamp = current

        current = startup_fingerprint(self.interface.code_path)
        if current is None:
            # The file will not parse, or has no startup at all. Half-typed code
            # is not an edited startup, and saying so mid-keystroke would train
            # the researcher to ignore the notice. The next parse settles it.
            return self.notice.visible
        stale = current != self.session.startup_fingerprint
        if stale:
            self.notice.show()
        self._notify_stale(stale)
        return stale

    def _notify_stale(self, stale) -> None:
        """Let the chrome show it too, since the strip is at the other end."""
        notify = getattr(self.app, "mark_startup_stale", None)
        if notify is not None:
            notify(stale)

    # -- watching the file -----------------------------------------------

    #: How often the code file is checked for a startup edit. Frequent enough
    #: that saving and looking up is enough to see the notice, cheap enough that
    #: it is one `stat` in between.
    POLL_MS = 700

    def _schedule_poll(self):
        self._poll_id = self.frame.after(self.POLL_MS, self._poll)

    def _poll(self):
        """Notice an edit without waiting for the researcher to click something.

        Saving the file is the moment they expect something to happen; making
        them click an unrelated element first is a puzzle, not a workflow.
        """
        self._poll_id = None
        if self.dispatcher is None:  # torn down between scheduling and firing
            return
        try:
            self.check_startup_staleness()
        finally:
            if self.dispatcher is not None:
                self._schedule_poll()

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
            self._checked_stamp = file_stamp(self.interface.code_path)
            self.notice.dismiss()
            self._notify_stale(False)
        self._redraw_plots()
        return ok

    def _after_invoke(self):
        self._redraw_plots()

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
