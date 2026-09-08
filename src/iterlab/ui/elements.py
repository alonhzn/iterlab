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


def build_button(parent, element, dispatcher):
    """A Tk button that responds to all three mouse buttons.

    Tk's own `command` option fires only for button 1, so middle and right
    clicks need their own bindings. `command` is kept for the left button
    rather than replaced with a <ButtonRelease-1> binding, because it is what
    `Button.invoke()` drives — the canonical way to activate a button, and the
    one tests use. Binding release-1 as well would fire the handler twice.

    All three use release rather than press, so every mouse button behaves the
    same way: the click counts when it completes on the widget.
    """
    widget = tk.Button(parent, text=element.label or element.name, font=base_font())
    name = element.name

    def fire(kind, **fields):
        dispatcher.invoke(
            f"on_{kind}_{name}", Event(kind=kind, element=name, **fields)
        )

    widget.configure(command=lambda: fire("clicked", button="left"))
    widget.bind("<ButtonRelease-2>", lambda _e: fire("clicked", button="middle"))
    widget.bind("<ButtonRelease-3>", lambda _e: fire("clicked", button="right"))
    widget.bind("<Double-Button-1>", lambda _e: fire("clicked", button="left", double=True))

    widget.bind("<Enter>", lambda _e: fire("hover"))
    widget.bind("<Motion>", lambda _e: fire("motion"))
    widget.bind("<Key>", lambda e: fire("key", key=e.keysym))

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
