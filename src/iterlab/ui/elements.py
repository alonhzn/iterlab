"""Element type -> Tk widget, and native events -> iterlab Events.

Controls are Tk widgets; an axes element is an embedded matplotlib canvas with the
standard navigation toolbar. No control is ever a matplotlib.widgets widget —
that decision capped the prior spike's vocabulary and made it slow as elements
were added (constitution Principle VI).

Plot events come from matplotlib rather than Tk because only matplotlib can give
**data coordinates**, which is the entire point of clicking a plot (R9).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.projections import register_projection

from ..layout.schema import SELECT_TYPES, parse_extensions
from ..runtime import remembered
from ..runtime.dispatch import Event
from . import dialogs, theme

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
        apply_style(
            self.widget,
            self.__dict__["_style"],
            default_bg=self._default_background(),
        )
        self._apply_visibility()

    def _default_background(self):
        """The colour to use when the researcher has not chosen one.

        None means the theme's surface colour. A type overrides this when its
        natural unstyled appearance is something else.
        """
        return None

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

    # -- surviving a rebuild ---------------------------------------------

    def _presentation(self) -> dict:
        """What this element looks like *now*, as opposed to in the layout file.

        A mode switch destroys every widget and builds new ones from the layout,
        so without this, anything set while the interface was running is lost:
        a colour a handler chose, or text somebody typed. The layout is where an
        element *starts*; this is where it currently is.
        """
        return {"style": self.__dict__["_style"]}

    def _restore(self, state) -> None:
        if "style" in state:
            self.__dict__["_style"] = state["style"]
        self._apply()


class _TextHandle(ElementHandle):
    """Shared by the element types that render text.

    Every one of them exposes the same `.text`, whatever Tk calls the underlying
    option: a Button and a Label keep their string in `-text`, an Entry keeps it
    in a variable, and a researcher should not have to know or care which. One
    name means `ev.<tag>.text` works without first remembering what kind of
    element `<tag>` is.
    """

    STYLE_PROPERTIES = STYLE_PROPERTY_NAMES

    def __getattr__(self, name):
        if name in STYLE_PROPERTY_NAMES:
            return getattr(self.__dict__["_style"], name)
        raise AttributeError(name)

    def _presentation(self) -> dict:
        state = super()._presentation()
        state["text"] = self.text
        return state

    def _restore(self, state) -> None:
        super()._restore(state)
        if "text" in state:
            self.text = state["text"]


class _CaptionHandle(_TextHandle):
    """Text held in the widget's own `-text` option: buttons and labels."""

    @property
    def text(self):
        return self.widget.cget("text")

    @text.setter
    def text(self, value):
        self.widget.configure(text=str(value))

    #: The layout calls it `label`; both names work.
    label = text


class ButtonHandle(_CaptionHandle):
    pass


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
    # `element.label`, not `label or tag`: an empty caption means an empty
    # button. Falling back to the tag made sense when a new element had no
    # text at all, but every type has a real default now, so the fallback only
    # ever fired when someone had deliberately cleared the text - which is the
    # one moment it is certainly not what they wanted.
    widget = tk.Button(parent, text=element.label, font=base_font())
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


class AxesHandle(Axes):
    """The handle for an axes element **is** a matplotlib `Axes`.

    Not an object that forwards to one. The difference is invisible for
    `ev.ax_0.plot(...)`, which worked either way, and decisive everywhere else:
    `isinstance(ev.ax_0, Axes)` is true, so any library that takes an `ax=`
    argument accepts it, and `plt.sca(ev.ax_0)` works. A forwarding wrapper
    fails all of that, and fails it at the researcher's call site rather than
    ours — which is precisely the kind of surprise choosing matplotlib was
    meant to avoid.

    Registered as a matplotlib *projection*, which is the supported way to have
    a figure create a particular Axes subclass. Everything iterlab adds is
    prefixed `_iterlab_`, so nothing can collide with matplotlib's own
    attributes, now or in a later release.
    """

    name = "iterlab"

    #: Part of the element-handle contract, same as on the Tk-backed handles:
    #: every style property a handle can set, it can also read. matplotlib owns
    #: how a plot *looks*, so visibility is the only one that is ours.
    STYLE_PROPERTIES = ("visible",)

    # Class-level defaults: matplotlib constructs this, so an instance exists
    # before iterlab has bound anything to it.
    _iterlab_element = None
    _iterlab_frame = None
    _iterlab_cids = ()
    _iterlab_visible = True

    def _iterlab_bind(self, element, frame):
        self._iterlab_element = element
        self._iterlab_frame = frame
        self._iterlab_visible = element.style.visible
        self._iterlab_apply_visibility()

    @property
    def tag(self):
        element = self._iterlab_element
        return element.tag if element is not None else None

    @property
    def element(self):
        return self._iterlab_element

    @property
    def widget(self):
        """The Tk frame holding the canvas and its toolbar."""
        return self._iterlab_frame

    @property
    def canvas(self):
        """The canvas currently drawing this axes.

        `Axes.figure` is matplotlib's own; the canvas is reached through it,
        and changes on every mode switch as the figure is attached to a new one.
        """
        figure = self.figure
        return None if figure is None else figure.canvas

    @property
    def visible(self):
        """Whether the *element* is shown, uniform with buttons and labels.

        Deliberately not matplotlib's `set_visible`, which hides the axes while
        leaving the frame and its toolbar in place. This hides the element, so
        `ev.ax_0.visible = False` means the same thing as it does on a button.
        matplotlib's own `get_visible`/`set_visible` are untouched and still do
        what matplotlib says they do.
        """
        return self._iterlab_visible

    @visible.setter
    def visible(self, value):
        self._iterlab_visible = bool(value)
        self._iterlab_apply_visibility()

    def _iterlab_apply_visibility(self):
        frame = self._iterlab_frame
        element = self._iterlab_element
        if frame is None or element is None:
            return
        if self._iterlab_visible:
            place(frame, element.position)
        else:
            frame.place_forget()

    def _presentation(self) -> dict:
        # matplotlib owns everything else about an axes, and the figure itself
        # already survives a rebuild - only whether the element is shown is ours.
        return {"visible": self._iterlab_visible}

    def _restore(self, state) -> None:
        if "visible" in state:
            self.visible = state["visible"]

    def disconnect(self):
        """Drop this canvas's event connections.

        The figure outlives the canvas, and so does its callback registry, so
        these must be released explicitly or they accumulate one set per mode
        switch and every click fires that many times.
        """
        canvas = self.canvas
        for cid in self._iterlab_cids:
            try:
                canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._iterlab_cids = ()


register_projection(AxesHandle)


def new_figure():
    """A figure whose axes is an `AxesHandle`, not a plain `Axes`."""
    figure = Figure(figsize=(4, 3), dpi=100)
    figure.add_subplot(111, projection=AxesHandle.name)
    return figure


def build_axes(parent, element, dispatcher, figure=None):
    """Build an axes element, reusing `figure` when the session supplies one.

    Reusing it is what keeps a drawn plot across a mode switch: the canvas dies
    with the widgets, the figure does not.
    """
    frame = tk.Frame(parent)
    if figure is None:
        figure = new_figure()
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

    axes._iterlab_cids = tuple(cids)
    axes._iterlab_bind(element, frame)
    canvas.draw()
    return axes


class LabelHandle(_CaptionHandle):
    """Text on screen. Set it from code: `ev.lbl_0.text = "..."`."""

    def _default_background(self):
        """Match whatever is behind it, so a label is text rather than a card.

        Tk has no real transparency, so "transparent" means painting the parent's
        own colour. Without this a label is a white rectangle sitting on the
        interface, which is exactly what a caption should not look like. Setting
        `ev.lbl_0.background` still wins - this is only the default.
        """
        try:
            return self.widget.master.cget("bg")
        except Exception:
            return None


def build_label(parent, element, dispatcher):
    """A label displays text. No handler is generated for it, but every
    interaction is still available if the researcher writes one (FR-017a)."""
    widget = tk.Label(
        parent,
        # Empty means empty. See the note in build_button.
        text=element.label,
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


class _BoxHandle(_TextHandle):
    """A box the researcher types into.

    Its text lives in a Tk variable rather than in a `-text` option, because
    that is where an Entry keeps what the person typed. `.text` hides the
    difference, so `ev.<tag>.text` reads the same whether `<tag>` is a button,
    a label or a box.
    """

    def __init__(self, element, widget, variable):
        super().__init__(element, widget)
        self.__dict__["variable"] = variable

    @property
    def text(self):
        return self.variable.get()

    @text.setter
    def text(self, value):
        self.variable.set("" if value is None else str(value))

    #: The layout calls it `label`; both names work.
    label = text


class TextBoxHandle(_BoxHandle):
    """A line of text the researcher types. Read it as `ev.edt_0.text`."""


class NumberBoxHandle(_BoxHandle):
    """A box that will only accept a number.

    `.text` is the string, as on every other element. `.value` is the number,
    which is what a researcher actually wants from it:

        ev.threshold = ev.val_0.value
    """

    @property
    def value(self):
        """The contents as a number, or 0 when the box is empty.

        Empty rather than an error: a researcher clearing the box to retype it
        is mid-edit, not mistaken, and a handler that reads it at that moment
        should get a number rather than an exception.
        """
        raw = self.variable.get().strip()
        if raw in ("", "-", ".", "-."):
            return 0
        number = float(raw)
        # An integer typed as an integer comes back as one: `range(ev.val_0.value)`
        # should work without the researcher casting it.
        return int(number) if number.is_integer() and "." not in raw else number

    @value.setter
    def value(self, number):
        self.variable.set(str(number))


def _accepts_number(candidate) -> bool:
    """Whether a proposed entry contents is on its way to being a number.

    Judged on what the box *would* contain after the keystroke, so this has to
    accept the half-written states a person passes through while typing: "",
    "-", "." and "-." are all on the way to a number, and refusing them would
    make the box impossible to type a negative or a decimal into.
    """
    if candidate in ("", "-", ".", "-."):
        return True
    if candidate.count(".") > 1 or candidate.count("-") > 1:
        return False
    if "-" in candidate and not candidate.startswith("-"):
        return False
    try:
        float(candidate)
    except ValueError:
        return False
    return True


def _build_box(parent, element, dispatcher, *, handle_class, numeric):
    widget_frame = tk.Entry(parent, font=base_font(), relief="solid", borderwidth=1)
    variable = tk.StringVar(master=parent, value=element.label or "")
    widget_frame.configure(textvariable=variable)

    if numeric:
        # Validated on the *proposed* contents rather than after the fact, so a
        # rejected keystroke never appears at all - no flicker, and the box is
        # never momentarily holding something that is not a number.
        check = parent.register(lambda proposed: _accepts_number(proposed))
        widget_frame.configure(validate="key", validatecommand=(check, "%P"))

    tag = element.tag

    def fire(kind, **fields):
        dispatcher.invoke(f"on_{kind}_{tag}", Event(kind=kind, tag=tag, **fields))

    widget_frame.bind("<ButtonRelease-1>", lambda _e: fire("clicked", button="left"))
    widget_frame.bind("<ButtonRelease-2>", lambda _e: fire("clicked", button="middle"))
    widget_frame.bind("<ButtonRelease-3>", lambda _e: fire("clicked", button="right"))
    widget_frame.bind("<Enter>", lambda _e: fire("hover"))
    widget_frame.bind("<Motion>", lambda _e: fire("motion"))
    # Bound to release, so `ev.<tag>.text` already holds the character typed by
    # the time the handler reads it. On press it would still be the old value.
    widget_frame.bind("<KeyRelease>", lambda e: fire("key", key=e.keysym))

    # `changed` means the researcher finished entering a value, not that a key
    # went down. Two triggers, deliberately not treated the same way:
    #
    #   Enter is a deliberate act, so it always runs the handler - that is how
    #   someone re-runs the same value on purpose.
    #
    #   Losing focus is incidental. Clicking past a box on the way to something
    #   else should not redraw a plot, so it runs only if the value actually
    #   moved since the handler last saw it.
    last_fired = {"value": variable.get()}

    def changed(force):
        current = variable.get()
        if not force and current == last_fired["value"]:
            return
        last_fired["value"] = current
        fire("changed")

    widget_frame.bind("<Return>", lambda _e: changed(force=True))
    widget_frame.bind("<KP_Enter>", lambda _e: changed(force=True))
    widget_frame.bind("<FocusOut>", lambda _e: changed(force=False))

    handle = handle_class(element, widget_frame, variable)
    handle._apply()
    return handle


def build_text_box(parent, element, dispatcher):
    """A box for a line of text (FR-017a: every interaction still available)."""
    return _build_box(
        parent, element, dispatcher, handle_class=TextBoxHandle, numeric=False
    )


def build_number_box(parent, element, dispatcher):
    """A box that refuses anything that is not on its way to being a number."""
    return _build_box(
        parent, element, dispatcher, handle_class=NumberBoxHandle, numeric=True
    )


class _SelectHandle(_CaptionHandle):
    """A button that opens an OS chooser and remembers what was picked.

    The caption is a caption, deliberately: it says "Select a File" before and
    after, and never becomes the filename. Showing the choice is one line in the
    researcher's own handler, and the generated stub shows it - which keeps the
    element's appearance something they control rather than something that
    changes under them.
    """

    #: Overridden per subclass: whether the thing chosen is a directory.
    EXPECTS_DIR = False

    def __init__(self, element, widget, interface_path):
        super().__init__(element, widget)
        self.__dict__["_interface_path"] = interface_path
        remembered_paths = remembered.load(interface_path)
        self.__dict__["_path"] = remembered_paths.get(element.tag, "")

    # -- what the researcher reads ---------------------------------------

    @property
    def path(self) -> str:
        """The chosen file or folder, or "" if there is not a usable one.

        Empty when nothing has been chosen *and* when what was chosen has since
        been deleted or moved. A path that no longer resolves is worse than no
        path: `if ev.fileselect.path:` would pass and the open would fail on
        something that looks perfectly valid.
        """
        stored = self.__dict__["_path"]
        return stored if remembered.usable(stored, expect_dir=self.EXPECTS_DIR) else ""

    @path.setter
    def path(self, value):
        self._record(str(value or ""))

    def _record(self, selection) -> None:
        self.__dict__["_path"] = selection
        remembered.remember(self.__dict__["_interface_path"], self.tag, selection)

    def _starting_directory(self) -> str:
        # The raw stored value, not `.path`: a file that was renamed still tells
        # us the folder to open, even though it is no longer a usable choice.
        return remembered.starting_directory(
            self.__dict__["_path"], expect_dir=self.EXPECTS_DIR
        )

    # -- surviving a rebuild ---------------------------------------------

    def _presentation(self) -> dict:
        state = super()._presentation()
        state["path"] = self.__dict__["_path"]
        return state

    def _restore(self, state) -> None:
        super()._restore(state)
        if "path" in state:
            self.__dict__["_path"] = state["path"]


class FileSelectHandle(_SelectHandle):
    EXPECTS_DIR = False

    def __init__(self, element, widget, interface_path):
        super().__init__(element, widget, interface_path)
        self.__dict__["_extensions"] = element.extensions

    @property
    def extensions(self) -> str:
        """Which files the chooser offers, e.g. "txt, csv". Empty means all."""
        return self.__dict__["_extensions"]

    @extensions.setter
    def extensions(self, value):
        self.__dict__["_extensions"] = "" if value is None else str(value)

    def _presentation(self) -> dict:
        state = super()._presentation()
        state["extensions"] = self.__dict__["_extensions"]
        return state

    def _restore(self, state) -> None:
        super()._restore(state)
        if "extensions" in state:
            self.__dict__["_extensions"] = state["extensions"]


class FolderSelectHandle(_SelectHandle):
    EXPECTS_DIR = True


def _build_select(parent, element, dispatcher, *, handle_class, interface_path):
    # `element.label`, not `label or tag`: an empty caption means an empty
    # button. Falling back to the tag made sense when a new element had no
    # text at all, but every type has a real default now, so the fallback only
    # ever fired when someone had deliberately cleared the text - which is the
    # one moment it is certainly not what they wanted.
    widget = tk.Button(parent, text=element.label, font=base_font())
    tag = element.tag
    handle_box = {}

    def choose(button="left"):
        """Open the chooser, then call the researcher's handler.

        In that order, and only on a real choice: the handler runs with
        `ev.<tag>.path` already set, and a cancelled dialog does nothing at all
        rather than firing a handler that would find the old value.
        """
        handle = handle_box.get("handle")
        if handle is None:  # pragma: no cover - the widget outliving its handle
            return
        if handle.EXPECTS_DIR:
            chosen = dialogs.ask_directory(
                parent=parent, initial_dir=handle._starting_directory()
            )
        else:
            chosen = dialogs.ask_open_file(
                parent=parent,
                initial_dir=handle._starting_directory(),
                extensions=parse_extensions(handle.extensions),
            )
        if not chosen:
            return
        handle._record(chosen)
        dispatcher.invoke(
            f"on_clicked_{tag}",
            Event(kind="clicked", tag=tag, button=button, path=chosen),
        )

    widget.configure(command=choose)
    widget.bind("<ButtonRelease-2>", lambda _e: choose("middle"))
    widget.bind("<ButtonRelease-3>", lambda _e: choose("right"))

    def fire(kind, **fields):
        dispatcher.invoke(f"on_{kind}_{tag}", Event(kind=kind, tag=tag, **fields))

    widget.bind("<Enter>", lambda _e: fire("hover"))
    widget.bind("<Motion>", lambda _e: fire("motion"))
    widget.bind("<Key>", lambda e: fire("key", key=e.keysym))

    handle = handle_class(element, widget, interface_path)
    handle_box["handle"] = handle
    handle._apply()
    return handle


def build_file_select(parent, element, dispatcher, interface_path=None):
    return _build_select(
        parent, element, dispatcher,
        handle_class=FileSelectHandle, interface_path=interface_path,
    )


def build_folder_select(parent, element, dispatcher, interface_path=None):
    return _build_select(
        parent, element, dispatcher,
        handle_class=FolderSelectHandle, interface_path=interface_path,
    )


BUILDERS = {
    "button": build_button,
    "axes": build_axes,
    "label": build_label,
    "text_box": build_text_box,
    "number_box": build_number_box,
    "file_select": build_file_select,
    "folder_select": build_folder_select,
}


def build(parent, element, dispatcher, figure=None, interface_path=None):
    if element.type == "axes":
        return build_axes(parent, element, dispatcher, figure=figure)
    if element.type in SELECT_TYPES:
        # These need to know which interface they belong to: what they remember
        # is stored per interface, outside the project folder.
        return BUILDERS[element.type](
            parent, element, dispatcher, interface_path=interface_path
        )
    return BUILDERS[element.type](parent, element, dispatcher)
