"""The session: what survives a mode switch.

Until now a session belonged to GUI mode, so toggling into the editor threw it
away and toggling back reloaded everything. That made a layout tweak cost a
full data load, which is the cost this project exists to remove — it was just
moved from "every code edit" to "every layout edit".

A session now belongs to the *interface*, and outlives both modes. What it owns:

* `ev` — the researcher's data, unchanged across any number of toggles.
* one matplotlib `Figure` per plot area, so drawn plots survive too. A Figure
  can be attached to a new canvas, which is what makes this possible at all.
* whether `on_startup` has run, so it runs once per session rather than once
  per visit to GUI mode.

What it does *not* own is widgets. Those belong to the mode that built them and
are destroyed with it; the session rebinds fresh ones on the way back in.
"""

from __future__ import annotations

from matplotlib.figure import Figure

from ..runtime.environment import Ev


class Session:
    """One researcher session, spanning any number of mode switches."""

    def __init__(self):
        self.ev = Ev()
        self.startup_done = False
        self._figures = {}

    # -- plot figures ----------------------------------------------------

    def figure_for(self, tag) -> Figure:
        """The Figure for this plot area, created once and reused.

        Reusing it is what keeps a drawn plot on screen across a mode switch:
        the canvas is thrown away with the widgets, the figure is not.
        """
        if tag not in self._figures:
            figure = Figure(figsize=(4, 3), dpi=100)
            figure.add_subplot(111)
            self._figures[tag] = figure
        return self._figures[tag]

    def axes_for(self, tag):
        return self.figure_for(tag).axes[0]

    def has_figure(self, tag) -> bool:
        return tag in self._figures

    # -- reconciling with a changed layout -------------------------------

    def retag(self, old, new) -> None:
        """Follow an element renamed in the editor.

        Without this the figure would be orphaned under the old tag and the
        plot would silently blank on the next switch.
        """
        if old in self._figures:
            self._figures[new] = self._figures.pop(old)
        self.ev._rename_element(old, new)

    def forget(self, tags) -> None:
        """Drop everything belonging to elements that no longer exist."""
        for tag in list(tags):
            self._figures.pop(tag, None)
        self.ev._unbind_elements(tags)

    def reconcile(self, live_tags) -> None:
        """Discard state for elements deleted since the last visit."""
        known = set(self._figures) | set(self.ev._element_tags)
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
        self._figures.clear()
