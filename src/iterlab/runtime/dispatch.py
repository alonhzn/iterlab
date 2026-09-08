"""The single guarded path every interaction passes through.

Three stages fail in three different ways, and conflating them is the defect
this project most wants not to repeat (research.md R4):

  load the module   -> any exception means the code is broken     -> report
  look up the name  -> AttributeError means no handler written    -> silence
  call the handler  -> any exception means the handler is broken  -> report

Nothing here catches an exception without first classifying it.

No GUI imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from .faults import HANDLER_RAISED, LOAD_FAILED, Fault
from .loader import NOT_DEFINED

#: The one handler iterlab calls itself rather than in response to interaction.
STARTUP_HANDLER = "on_startup"


@dataclass(frozen=True)
class Event:
    """What just happened, normalized across Tk and matplotlib.

    A handler signature therefore never depends on how an element is
    implemented, which keeps the toolkit out of the public surface (R9).
    """

    kind: str
    element: str
    button: str | None = None
    x: float | None = None
    y: float | None = None
    key: str | None = None
    double: bool = False


class Dispatcher:
    """Resolves a handler by name at call time and invokes it, guarded.

    Holds no function object — only the loader and the sink. That is what makes
    a reloaded handler take effect with no rebinding step.
    """

    def __init__(self, loader, ev, sink, before_invoke=None, after_invoke=None):
        self.loader = loader
        self.ev = ev
        self.sink = sink
        #: Hook the runner uses for the deferred first startup (FR-026d). Runs
        #: before any interaction, and is cleared once startup has succeeded.
        self.before_invoke = before_invoke
        #: Hook the runner uses to repaint whatever the handler drew. Researcher
        #: code that calls `ev.some_plot.plot(...)` changes the figure but does
        #: not repaint it; something has to, and it cannot be this layer, which
        #: imports no GUI module.
        self.after_invoke = after_invoke
        self._failing = set()
        self._in_hook = False

    def invoke(self, handler_name, event=None, args=None):
        """Run one handler. Returns True if researcher code actually ran.

        Never raises on the researcher's account: the process surviving is the
        whole point (constitution Principle III).
        """
        element = event.element if event is not None else None

        # A startup that never completed gets another chance before anything
        # else runs, so a typo there cannot strand the session (FR-026d).
        # Never fires for startup itself: the hook's whole job is to run startup,
        # so re-entering it there would report a launch-time fault twice.
        if (
            self.before_invoke is not None
            and not self._in_hook
            and handler_name != STARTUP_HANDLER
        ):
            self._in_hook = True
            try:
                self.before_invoke()
            finally:
                self._in_hook = False

        # Stage 1 — the module.
        if not self.loader.refresh():
            self._report(
                Fault.from_exception(
                    self.loader.load_error, kind=LOAD_FAILED, element=element
                )
            )
            return False

        # Stage 2 — the name. Absence is normal and silent.
        handler = self.loader.resolve(handler_name)
        if handler is NOT_DEFINED:
            return False

        # Stage 3 — the call.
        call_args = args if args is not None else ((self.ev, event) if event else (self.ev,))
        try:
            handler(*call_args)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            self._report(
                Fault.from_exception(
                    exc,
                    kind=HANDLER_RAISED,
                    element=element,
                    interaction=event.kind if event else None,
                )
            )
            return False
        finally:
            # Researcher code ran, so whatever it drew must be shown — including
            # when it went on to raise, since work done before the exception is
            # still on the figure and hiding it would be confusing.
            if self.after_invoke is not None:
                self.after_invoke()

        self._clear(element)
        return True

    # -- fault bookkeeping ------------------------------------------------

    def _report(self, fault):
        self._failing.add(fault.element)
        self.sink.report(fault)

    def _clear(self, element):
        """Retract a stale report once corrected code runs (FR-033b).

        Without this the window accumulates warnings and stops telling the
        researcher the truth about the current state.
        """
        if element in self._failing:
            self._failing.discard(element)
            self.sink.clear(element)
        elif None in self._failing:
            # A module-level failure is not attributable to one element, so any
            # successful call means the file loads again.
            self._failing.discard(None)
            self.sink.clear(None)

    def handler_for(self, element_name, interaction):
        """A callback bound to a name, never to a function.

        The closure captures strings only, so it stays correct across reloads.
        """
        handler_name = f"on_{interaction}_{element_name}"

        def callback(event=None, **kwargs):
            ev = event or Event(kind=interaction, element=element_name, **kwargs)
            return self.invoke(handler_name, ev)

        return callback
