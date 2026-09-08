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
from . import theme

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


ANCHORS = {"left": "w", "center": "center", "right": "e"}

#: Every style property a text-bearing handle exposes to researcher code.
STYLE_PROPERTY_NAMES = (
    "background", "text_color", "edge", "edge_width",
    "font", "font_size", "bold", "italic", "align", "enabled", "visible",
)


def resolve_font(style):
    """Build a Tk font from a Style, falling back to the theme's defaults."""
    # BASE_FONT_SIZE, not the theme's chrome size: the editor's own furniture
    # is deliberately smaller than the elements a researcher draws.
    return tkfont.Font(
        family=style.font or theme.FONT[0],
        size=style.font_size or BASE_FONT_SIZE,
        weight="bold" if style.bold else "normal",
        slant="italic" if style.italic else "roman",
    )


def apply_style(widget, style, *, default_bg=None, default_fg=None):
    """Push a Style onto a Tk widget. Unset properties keep the theme value."""
    options = {
        "bg": style.background or default_bg or theme.SURFACE,
        "fg": style.text_color or default_fg or theme.TEXT,
        "font": resolve_font(style),
        "highlightthickness": style.edge_width,
        "highlightbackground": style.edge or theme.BORDER_STRONG,
        "highlightcolor": style.edge or theme.BORDER_STRONG,
        "anchor": ANCHORS.get(style.align, "center"),
        "state": "normal" if style.enabled else "disabled",
    }
    for option, value in options.items():
        try:
            widget.configure(**{option: value})
        except tk.TclError:
            # Not every widget takes every option. Skipping one is correct, not
            # a failure — a Frame has no `state`, a Label no `activebackground`.
            continue


class ElementHandle:
    """What the researcher reaches through `ev.<tag>`.

    Style properties are settable from code. Setting one changes the **live
    widget** and never writes back to the layout file: the layout holds the
    starting appearance, and research code overrides it for the session
    (Principle II — code never alters the layout).
    """

    #: Which style properties this handle exposes. Set per subclass.
    STYLE_PROPERTIES = ()

    def __init__(self, element, widget):
        self.__dict__["element"] = element
        self.__dict__["widget"] = widget
        self.__dict__["_style"] = element.style

    @property
    def tag(self):
        return self.element.tag

    @property
    def style(self):
        return self.__dict__["_style"]

    def _restyle(self, **changes):
        from dataclasses import replace

        self.__dict__["_style"] = replace(self.__dict__["_style"], **changes)
        self._apply()

    def _apply(self):
        apply_style(self.widget, self.__dict__["_style"])
        self._apply_visibility()

    def _apply_visibility(self):
        if self.__dict__["_style"].visible:
            place(self.widget, self.element.position)
        else:
            self.widget.place_forget()

    def __setattr__(self, name, value):
        if name in self.STYLE_PROPERTIES:
            self._restyle(**{name: value})
            return
        object.__setattr__(self, name, value)


class _TextHandle(ElementHandle):
    """Shared by the element types that render text."""

    STYLE_PROPERTIES = STYLE_PROPERTY_NAMES

    def __getattr__(self, name):
        if name in STYLE_PROPERTY_NAMES:
            return getattr(self.__dict__["_style"], name)
        raise AttributeError(name)


class ButtonHandle(_TextHandle):
    @property
    def text(self):
        return self.widget.cget("text")

    @text.setter
    def text(self, value):
        self.widget.configure(text=str(value))

    #: The layout calls it `label`; both names work.
    label = text


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
    widget = tk.Button(parent, text=element.label or element.tag, font=base_font())
    tag = element.tag

    def fire(kind, **fields):
        dispatcher.invoke(
            f"on_{kind}_{tag}", Event(kind=kind, tag=tag, **fields)
        )

    widget.configure(command=lambda: fire("clicked", button="left"))
    widget.bind("<ButtonRelease-2>", lambda _e: fire("clicked", button="middle"))
    widget.bind("<ButtonRelease-3>", lambda _e: fire("clicked", button="right"))
    widget.bind("<Double-Button-1>", lambda _e: fire("clicked", button="left", double=True))

    widget.bind("<Enter>", lambda _e: fire("hover"))
    widget.bind("<Motion>", lambda _e: fire("motion"))
    widget.bind("<Key>", lambda e: fire("key", key=e.keysym))

    handle = ButtonHandle(element, widget)
    handle._apply()
    return handle


class PlotHandle(ElementHandle):
    STYLE_PROPERTIES = ("visible",)

    """Exposes the matplotlib Axes directly.

    Anything else would mean researchers learning an iterlab plotting API, which
    is exactly what choosing matplotlib was meant to avoid.
    """

    def __init__(self, element, widget, figure, axes, canvas):
        super().__init__(element, widget)
        self.__dict__["figure"] = figure
        self.__dict__["axes"] = axes
        self.__dict__["canvas"] = canvas

    def _apply(self):
        # matplotlib owns how a plot looks; only visibility is ours.
        self._apply_visibility()

    def disconnect(self):
        """Drop this canvas's event connections.

        The figure outlives the canvas, and so does its callback registry, so
        these must be released explicitly or they accumulate one set per mode
        switch and every click fires that many times.
        """
        for cid in self.__dict__.get("_cids", ()):
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self.__dict__["_cids"] = []

    def __getattr__(self, item):
        # A style property this handle can set must also be readable; the Axes
        # knows nothing about `visible`, so answer that here before delegating.
        if item in self.STYLE_PROPERTIES:
            return getattr(self.__dict__["_style"], item)
        # Delegate to the Axes so `ev.spectrum.plot(...)` works.
        return getattr(self.__dict__["axes"], item)


def build_plot_area(parent, element, dispatcher, figure=None):
    """Build a plot area, reusing `figure` when the session supplies one.

    Reusing it is what keeps a drawn plot across a mode switch: the canvas dies
    with the widgets, the figure does not.
    """
    frame = tk.Frame(parent)
    if figure is None:
        figure = Figure(figsize=(4, 3), dpi=100)
        figure.add_subplot(111)
    axes = figure.axes[0]
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # The standard pan/zoom toolbar, available with no handler written (FR-017e).
    toolbar = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side="bottom", fill="x")

    tag = element.tag

    def fire(kind, mpl_event, **extra):
        dispatcher.invoke(
            f"on_{kind}_{tag}",
            Event(
                kind=kind,
                tag=tag,
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

    # Keep the connection ids. A figure's callback registry is shared with every
    # canvas it is ever attached to, so without disconnecting these on teardown
    # a click would fire the handler once per mode switch ever made.
    cids = [
        canvas.mpl_connect("button_press_event", on_press),
        canvas.mpl_connect("motion_notify_event", on_motion),
        canvas.mpl_connect("key_press_event", on_key),
        canvas.mpl_connect(
            "axes_enter_event",
            lambda e: fire("hover", e) if e.inaxes is axes else None,
        ),
    ]

    handle = PlotHandle(element, frame, figure, axes, canvas)
    handle.__dict__["_cids"] = cids
    handle._apply_visibility()
    canvas.draw()
    return handle


class LabelHandle(_TextHandle):
    """Text on screen. Set it from code: `ev.title.text = "..."`."""

    @property
    def text(self):
        return self.widget.cget("text")

    @text.setter
    def text(self, value):
        self.widget.configure(text=str(value))

    #: The layout calls it `label`; both names work.
    label = text


def build_label(parent, element, dispatcher):
    """A label displays text. No handler is generated for it, but every
    interaction is still available if the researcher writes one (FR-017a)."""
    widget = tk.Label(
        parent,
        text=element.label or element.tag,
        font=base_font(),
        anchor="w",
        justify="left",
        bg=theme.SURFACE,
        fg=theme.TEXT,
    )
    tag = element.tag

    def fire(kind, **fields):
        dispatcher.invoke(f"on_{kind}_{tag}", Event(kind=kind, tag=tag, **fields))

    widget.bind("<ButtonRelease-1>", lambda _e: fire("clicked", button="left"))
    widget.bind("<ButtonRelease-2>", lambda _e: fire("clicked", button="middle"))
    widget.bind("<ButtonRelease-3>", lambda _e: fire("clicked", button="right"))
    widget.bind("<Enter>", lambda _e: fire("hover"))
    widget.bind("<Motion>", lambda _e: fire("motion"))
    widget.bind("<Key>", lambda e: fire("key", key=e.keysym))

    handle = LabelHandle(element, widget)
    handle._apply()
    return handle


BUILDERS = {
    "button": build_button,
    "plot_area": build_plot_area,
    "label": build_label,
}


def build(parent, element, dispatcher, figure=None):
    if element.type == "plot_area":
        return build_plot_area(parent, element, dispatcher, figure=figure)
    return BUILDERS[element.type](parent, element, dispatcher)
