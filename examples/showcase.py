"""A showcase interface: three plots, a list, a handful of controls, and the loop.

    iterlab examples/showcase

Draw the layout in editor mode, use it in GUI mode, and switch with the toggle
in the top-left corner. Everything below is ordinary Python.

The point of the paradigm is in `on_startup`. It builds the data once per
session. Every handler under it only *draws*, so editing this file and clicking
a button re-runs the drawing against data that is already in memory - no reload,
no waiting, no losing where you were.
"""

import numpy as np

#: How long a slice of signal the wave plot shows, in seconds.
SPAN = 2.0

DEFAULT_FREQUENCIES = "1, 2.5, 4"
DEFAULT_SAMPLES = "240"
DEFAULT_NOISE = "0.25"

CATEGORIES = ("north", "east", "south", "west", "centre")

#: Bar colours. Picking regions in the list greys out the others, so the
#: picked bars stay in the same blue the list selects them in.
BAR = "#2f6feb"
DIMMED = "#c4cad2"


# -- the session ------------------------------------------------------------


def on_startup(ev):
    """Runs once, when the interface opens. The expensive half lives here.

    Nothing in here depends on a control, so nothing in here has to run again
    when one changes.
    """
    ev.rng = np.random.default_rng(7)
    ev.t = np.linspace(0, SPAN, 1200)
    ev.reading = ev.rng.normal(1.0, 0.25, size=len(CATEGORIES))
    fill_regions(ev)
    redraw(ev)


# -- the list of regions ----------------------------------------------------


def fill_regions(ev):
    """One row per region, its reading beside it, best and worst marked.

    The rows are written once and then *rewritten* in place: replacing a row's
    text keeps it selected, so shuffling the data does not lose what you picked.
    Its style is set afresh, since the best and the worst move with the data.
    """
    lst = ev.lst_regions
    rows = [f"{name}   {value:.2f}" for name, value in zip(CATEGORIES, ev.reading)]
    if lst.length != len(rows):
        lst.clear()
        lst.extend(rows)
    for index, row in enumerate(rows):
        lst[index] = row
        lst.style_line(index, text_color=None, highlight=None, bold=None)

    lst.style_line(int(np.argmax(ev.reading)), text_color="#1a7f37", bold=True)
    lst.style_line(int(np.argmin(ev.reading)), text_color="#b42318", highlight="#fde8e8")


def on_clicked_lst_regions(ev, event):
    """Click a region to pick its bar; Ctrl+click to pick several."""
    draw_bars(ev)


# -- reading the controls ---------------------------------------------------


def frequencies(ev):
    """The frequency box as a list of numbers.

    Anything that is not a number is skipped rather than raising: this is a box
    someone is typing into, and half-typed input is normal.
    """
    found = []
    for piece in str(ev.edt_freq.text).replace(";", ",").split(","):
        try:
            found.append(float(piece.strip()))
        except ValueError:
            continue
    return found or [1.0]


def samples(ev):
    return max(int(ev.val_points.value), 5)


def noise(ev):
    return max(ev.val_noise.value, 0.0)


# -- drawing ----------------------------------------------------------------


def draw_waves(ev):
    """One sine per frequency, on a real matplotlib Axes."""
    ax = ev.ax_waves
    ax.clear()
    for hertz in frequencies(ev):
        ax.plot(ev.t, np.sin(2 * np.pi * hertz * ev.t), lw=1.6, label=f"{hertz:g} Hz")
    ax.set_title("Sines, over two seconds", fontsize=10, loc="left")
    ax.set_xlim(0, SPAN)
    # Headroom above 1.0 so the legend sits over empty space rather than over
    # the curves. An axis label along the bottom is clipped at this size.
    ax.set_ylim(-1.3, 2.0)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, ncol=len(frequencies(ev)), loc="upper right", framealpha=0.9)
    ax.tick_params(labelsize=8)


def draw_scatter(ev):
    """A cloud whose spread is the noise control, coloured by distance."""
    ax = ev.ax_scatter
    ax.clear()
    count = samples(ev)
    x = ev.rng.normal(0, 1, count)
    y = 0.7 * x + ev.rng.normal(0, noise(ev) + 0.05, count)
    ax.scatter(x, y, c=np.hypot(x, y), cmap="viridis", s=16, alpha=0.8)
    ax.set_title("Scatter", fontsize=10, loc="left")
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)


def draw_bars(ev):
    """Response per region, with the noise control as the error bars.

    Picking regions in the list greys out the rest. Multi-select is ticked in
    the editor, so `.selected` is a tuple of row indexes, `()` for none.
    """
    ax = ev.ax_bars
    ax.clear()
    picked = ev.lst_regions.selected
    ax.bar(
        CATEGORIES,
        ev.reading,
        yerr=noise(ev) * ev.reading,
        color=[BAR if not picked or i in picked else DIMMED for i in range(len(CATEGORIES))],
        alpha=0.85,
        capsize=4,
    )
    names = ", ".join(CATEGORIES[i] for i in picked)
    ax.set_title(
        f"Response by region - {names}" if names else "Response by region",
        fontsize=10, loc="left",
    )
    ax.set_ylabel("gain", fontsize=8)
    ax.grid(alpha=0.25, axis="y")
    ax.tick_params(labelsize=8)


def redraw(ev):
    draw_waves(ev)
    draw_scatter(ev)
    draw_bars(ev)
    count = len(frequencies(ev))
    ev.lbl_status.text = (
        f"{count} sine{'' if count == 1 else 's'}, {samples(ev)} samples, "
        f"noise {noise(ev):.2f}"
    )


# -- the buttons ------------------------------------------------------------


def on_clicked_cmd_redraw(ev, event):
    redraw(ev)


def on_clicked_cmd_shuffle(ev, event):
    """New draws from the same generator, so every plot moves but nothing reloads."""
    ev.reading = ev.rng.normal(1.0, 0.25, size=len(CATEGORIES))
    fill_regions(ev)
    redraw(ev)


def on_clicked_cmd_reset(ev, event):
    ev.edt_freq.text = DEFAULT_FREQUENCIES
    ev.val_points.text = DEFAULT_SAMPLES
    ev.val_noise.text = DEFAULT_NOISE
    ev.lst_regions.selected = ()
    redraw(ev)


# -- the boxes --------------------------------------------------------------
# Not on every keystroke: these fire when you press Enter or leave the box.


def on_changed_edt_freq(ev, event):
    draw_waves(ev)
    redraw(ev)


def on_changed_val_points(ev, event):
    redraw(ev)


def on_changed_val_noise(ev, event):
    redraw(ev)


if __name__ == "__main__":
    # So this opens straight from an IDE's run button, the same as
    # `iterlab examples/showcase` from a terminal.
    import iterlab

    iterlab.run(__file__)
