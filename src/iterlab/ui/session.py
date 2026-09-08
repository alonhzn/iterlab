"""The session: what survives a mode switch.

Until now a session belonged to GUI mode, so toggling into the editor threw it
away and toggling back reloaded everything. That made a layout tweak cost a
full data load, which is the cost this project exists to remove — it was just
moved from "every code edit" to "every layout edit".

A session now belongs to the *interface*, and outlives both modes. What it owns:

* `ev` — the researcher's data, unchanged across any number of toggles.
* one matplotlib `Figure` per axes element, so drawn plots survive too. A Figure
  can be attached to a new canvas, which is what makes this possible at all.
* whether `on_startup` has run, so it runs once per session rather than once
  per visit to GUI mode.

What it does *not* own is widgets. Those belong to the mode that built them and
are destroyed with it; the session rebinds fresh ones on the way back in.
"""

from __future__ import annotations

from ..runtime.environment import Ev


class Session:
    """One researcher session, spanning any number of mode switches."""

    def __init__(self):
        self.ev = Ev()
        self.startup_done = False
        #: Fingerprint of the startup code as it was when it last ran, so an
        #: edit to it can be noticed and offered rather than silently ignored.
        self.startup_fingerprint = None
        self._figures = {}
        #: How each element looked when its widgets were last destroyed, so a
        #: mode switch does not undo what the running interface did.
        self._presentation = {}

    # -- plot figures ----------------------------------------------------

    def figure_for(self, tag):
        """The Figure for this axes element, created once and reused.

        Reusing it is what keeps a drawn plot on screen across a mode switch:
        the canvas is thrown away with the widgets, the figure is not.
        """
        if tag not in self._figures:
            # Built by the element module so the axes is an AxesHandle, which is
            # what makes `ev.ax_0` a real matplotlib Axes.
            from .elements import new_figure

            self._figures[tag] = new_figure()
        return self._figures[tag]

    def axes_for(self, tag):
        return self.figure_for(tag).axes[0]

    def has_figure(self, tag) -> bool:
        return tag in self._figures

    # -- what the running interface changed ------------------------------

    def remember(self, tag, element, state) -> None:
        """Keep how an element looked, alongside what the layout said at the time.

        Both halves are needed. The state is what to put back; the layout values
        are what makes it possible to tell later whether the researcher has
        since changed their mind in the editor.
        """
        self._presentation[tag] = {
            "state": dict(state),
            "label": element.label,
            "style": element.style,
        }

    def presentation_for(self, tag, element) -> dict:
        """What to reapply to a freshly built widget for `tag`.

        Anything the researcher has edited in the editor since is dropped: an
        explicit change to the layout is a decision, and it must win over a
        value the interface happened to be holding. Editing a button's caption
        and having the old one come straight back would be its own bug report.
        """
        remembered = self._presentation.get(tag)
        if remembered is None:
            return {}
        state = dict(remembered["state"])
        if element.label != remembered["label"]:
            state.pop("text", None)
        if element.style != remembered["style"]:
            state.pop("style", None)
            state.pop("visible", None)
        return state

    # -- reconciling with a changed layout -------------------------------

    def retag(self, old, new) -> None:
        """Follow an element renamed in the editor.

        Without this the figure would be orphaned under the old tag and the
        plot would silently blank on the next switch.
        """
        if old in self._figures:
            self._figures[new] = self._figures.pop(old)
        if old in self._presentation:
            self._presentation[new] = self._presentation.pop(old)
        self.ev._rename_element(old, new)

    def forget(self, tags) -> None:
        """Drop everything belonging to elements that no longer exist."""
        for tag in list(tags):
            self._figures.pop(tag, None)
            self._presentation.pop(tag, None)
        self.ev._unbind_elements(tags)

    def reconcile(self, live_tags) -> None:
        """Discard state for elements deleted since the last visit."""
        known = set(self._figures) | set(self._presentation) | set(self.ev._element_tags)
        self.forget(known - set(live_tags))

    # -- lifecycle -------------------------------------------------------

    def restart(self) -> None:
        """Throw the session away and begin again.

        This is how a change to `on_startup` takes effect. Toggling no longer
        does it, because toggling now deliberately preserves everything —
        so there has to be one explicit way to say "start over".
        """
        self.ev = Ev()
        self.startup_done = False
        self.startup_fingerprint = None
        self._figures.clear()
        self._presentation.clear()
