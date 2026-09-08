"""Element type -> Tk widget, and native events -> iterlab Events.

Controls are Tk widgets; plot areas are an embedded matplotlib canvas with the
standard navigation toolbar. No control is ever a matplotlib.widgets widget —
that decision capped the prior spike's vocabulary and made it slow as elements
were added (constitution Principle VI).

Plot events come from matplotlib rather than Tk because only matplotlib can give
**data coordinates**, which is the entire point of clicking a plot (R9).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from ..runtime.dispatch import Event

#: Fonts are fixed in points and never scaled, so text stays readable at every
#: window size while geometry scales with it (FR-021b).
BASE_FONT_SIZE = 10

_MPL_BUTTON = {1: "left", 2: "middle", 3: "right"}
_TK_BUTTON = {1: "left", 2: "middle", 3: "right"}


def base_font():
    return tkfont.Font(family="TkDefaultFont", size=BASE_FONT_SIZE)


def place(widget, rect) -> None:
    """Position by fractions of the parent, origin bottom-left.

    `place` with relative options recomputes geometry on every resize, so
    proportional scaling (FR-021a) needs no resize handler at all (R8).
    """
    widget.place(
        relx=rect.left,
        rely=1.0 - rect.bottom - rect.height,  # Tk's origin is top-left
        relwidth=rect.width,
        relheight=rect.height,
    )


class ElementHandle:
    """What the researcher reaches through `ev.<name>`."""

    def __init__(self, element, widget):
        self.element = element
        self.widget = widget

    @property
    def name(self):
        return self.element.name


class ButtonHandle(ElementHandle):
    @property
    def label(self):
        return self.widget.cget("text")

    @label.setter
    def label(self, text):
        self.widget.configure(text=text)


def _bind_tk_events(widget, element, dispatcher):
    """Universal interaction set on a Tk control (FR-017a)."""
    name = element.name

    def fire(kind, **kwargs):
        dispatcher.invoke(f"on_{kind}_{name}", Event(kind=kind, element=name, **kwargs))

    widget.bind("<Button-1>", lambda e: fire("clicked", button=_TK_BUTTON.get(e.num, "left")))
    widget.bind("<Button-2>", lambda e: fire("clicked", button="middle"))
    widget.bind("<Button-3>", lambda e: fire("clicked", button="right"))
    widget.bind("<Double-Button-1>", lambda e: fire("clicked", button="left", double=True))
    widget.bind("<Enter>", lambda e: fire("hover"))
    widget.bind("<Motion>", lambda e: fire("motion"))
    widget.bind("<Key>", lambda e: fire("key", key=e.keysym))


def build_button(parent, element, dispatcher):
    widget = tk.Button(parent, text=element.label or element.name, font=base_font())
    # The click handler goes through `command` so that Button.invoke() in tests
    # exercises the same path a real click does.
    widget.configure(
        command=lambda: dispatcher.invoke(
            f"on_clicked_{element.name}",
            Event(kind="clicked", element=element.name, button="left"),
        )
    )
    for sequence, kind in (("<Enter>", "hover"), ("<Motion>", "motion"), ("<Key>", "key")):
        widget.bind(
            sequence,
            lambda e, k=kind: dispatcher.invoke(
                f"on_{k}_{element.name}",
                Event(
                    kind=k,
                    element=element.name,
                    key=getattr(e, "keysym", None) if k == "key" else None,
                ),
            ),
        )
    place(widget, element.position)
    return ButtonHandle(element, widget)


class PlotHandle(ElementHandle):
    """Exposes the matplotlib Axes directly.

    Anything else would mean researchers learning an iterlab plotting API, which
    is exactly what choosing matplotlib was meant to avoid.
    """

    def __init__(self, element, widget, figure, axes, canvas):
        super().__init__(element, widget)
        self.figure = figure
        self.axes = axes
        self.canvas = canvas

    def __getattr__(self, item):
        # Delegate to the Axes so `ev.spectrum.plot(...)` works.
        return getattr(self.__dict__["axes"], item)


def build_plot_area(parent, element, dispatcher):
    frame = tk.Frame(parent)
    figure = Figure(figsize=(4, 3), dpi=100)
    axes = figure.add_subplot(111)
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # The standard pan/zoom toolbar, available with no handler written (FR-017e).
    toolbar = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side="bottom", fill="x")

    name = element.name

    def fire(kind, mpl_event, **extra):
        dispatcher.invoke(
            f"on_{kind}_{name}",
            Event(
                kind=kind,
                element=name,
                x=getattr(mpl_event, "xdata", None),
                y=getattr(mpl_event, "ydata", None),
                **extra,
            ),
        )

    def on_press(mpl_event):
        if mpl_event.inaxes is not axes:
            return
        fire(
            "clicked",
            mpl_event,
            button=_MPL_BUTTON.get(getattr(mpl_event, "button", 1), "left"),
            double=bool(getattr(mpl_event, "dblclick", False)),
        )

    def on_motion(mpl_event):
        if mpl_event.inaxes is not axes:
            return
        fire("motion", mpl_event)

    def on_key(mpl_event):
        fire("key", mpl_event, key=getattr(mpl_event, "key", None))

    canvas.mpl_connect("button_press_event", on_press)
    canvas.mpl_connect("motion_notify_event", on_motion)
    canvas.mpl_connect("key_press_event", on_key)
    canvas.mpl_connect(
        "axes_enter_event",
        lambda e: fire("hover", e) if e.inaxes is axes else None,
    )

    place(frame, element.position)
    canvas.draw()
    return PlotHandle(element, frame, figure, axes, canvas)


BUILDERS = {"button": build_button, "plot_area": build_plot_area}


def build(parent, element, dispatcher):
    return BUILDERS[element.type](parent, element, dispatcher)
