"""A scrollable column, for the editor sidebar.

Without this, Tk's packer simply stops mapping children once they no longer
fit. The widgets do not overflow or clip — they silently cease to exist on
screen, with no error anywhere. At the default 800x450 window the properties
panel was past that line, so the geometry fields were absent rather than
scrolled out of view.

Scrolling also means the sidebar keeps working as element types and properties
are added, instead of quietly losing whatever falls off the bottom.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme


class ScrollableColumn:
    """A fixed-width column whose contents scroll vertically when too tall.

    Add children to `.inner`.
    """

    def __init__(self, parent, width):
        self.width = width
        self.outer = tk.Frame(parent, width=width, bg=theme.BG)
        self.outer.pack_propagate(False)

        self.canvas = tk.Canvas(
            self.outer, bg=theme.BG, highlightthickness=0, bd=0, width=width
        )
        self.scrollbar = ttk.Scrollbar(
            self.outer, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self._on_scroll_needed)

        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=theme.BG)
        self._window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw", width=width
        )

        self.inner.bind("<Configure>", self._on_inner_resize)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_wheel)      # Windows, macOS
            widget.bind("<Button-4>", self._on_wheel)        # X11 up
            widget.bind("<Button-5>", self._on_wheel)        # X11 down

        self._scrollbar_shown = False

    # -- geometry --------------------------------------------------------

    def _on_inner_resize(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_scrollbar()

    def _on_canvas_resize(self, event):
        # Keep the inner frame exactly as wide as the visible area, minus the
        # scrollbar when one is showing, so nothing is cut off horizontally.
        self.canvas.itemconfigure(self._window, width=event.width)
        self._sync_scrollbar()

    def _on_scroll_needed(self, first, last):
        self.scrollbar.set(first, last)
        self._sync_scrollbar()

    def _sync_scrollbar(self):
        """Show the scrollbar only when there is something to scroll to."""
        needed = self.inner.winfo_reqheight() > self.canvas.winfo_height()
        if needed and not self._scrollbar_shown:
            self.scrollbar.pack(side="right", fill="y")
            self._scrollbar_shown = True
        elif not needed and self._scrollbar_shown:
            self.scrollbar.pack_forget()
            self._scrollbar_shown = False

    def _on_wheel(self, event):
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def bind_wheel_to_children(self):
        """Let the wheel scroll from anywhere in the column.

        Children swallow the event otherwise, so the wheel would only work
        over the gaps between widgets.
        """

        def walk(widget):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(sequence, self._on_wheel, add="+")
            for child in widget.winfo_children():
                walk(child)

        walk(self.inner)
