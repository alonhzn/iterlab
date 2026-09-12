"""A mode switch renders each plot once, and refuses to start twice.

Both modes come from one remembered size, so every switch resizes the window by
the toolbar's width. `geometry` only *asks* for that size - Tk applies it on a
later pass - so for a while the new mode was built at the old width and every
plot on screen rendered a second time when the resize finally landed. Three
plots cost nine renders where six would do, and the switch went from feeling
instant to feeling like a wait on anything with several plots.

Landing the resize first means running the event loop mid-switch, which is why
`busy` exists: between teardown and the new mode, a second click really can
arrive, and a rebuild starting inside a rebuild tears down what the outer one
is still holding.

Counting renders rather than timing them. A timing budget on a shared CI runner
is a flake; the count is exact and is the thing that actually changed.
"""

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CODE = """def on_startup(ev):
    for tag in ("ax_0", "ax_1", "ax_2"):
        getattr(ev, tag).plot([0, 1, 2], [0, 1, 0])
"""


@pytest.fixture(scope="module")
def opened(tk_root, tmp_path_factory):
    """Three plots, drawn, in GUI mode - the shape that made this visible.

    Module-scoped for the same reason the showcase tests are: every app built
    on the shared root leaves a figure canvas and a matplotlib toolbar per plot
    behind it, each toolbar holding a handful of Tk images, and enough of them
    take the Tcl interpreter down in some unrelated file later. Six apps of
    three plots is enough to do it.
    """
    from iterlab.app import open_interface

    work = tmp_path_factory.mktemp("switch")
    tk_root.deiconify()
    app = open_interface(str(work / "plots"), _show=False, _root=tk_root)
    for index in range(3):
        app.built.create_element("axes", Rect(0.05, 0.05 + index * 0.3, 0.5, 0.25))
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    app.root.update()
    yield app
    app.close()
    tk_root.withdraw()
    for child in tk_root.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass


@pytest.fixture
def plots(opened):
    """The shared app, back in GUI mode and with no patches left on it."""
    if opened.mode != "gui":
        opened.toggle()
        opened.root.update()
    yield opened
    # Two tests replace `_construct` on the instance to observe a switch from
    # the inside. Left in place it would observe every later test as well.
    opened.__dict__.pop("_construct", None)
    if opened.mode != "gui":
        opened.toggle()
        opened.root.update()


@pytest.fixture
def renders(monkeypatch):
    """Count every canvas render, whoever asks for it."""
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    counted = []
    original = FigureCanvasTkAgg.draw

    def draw(self, *args, **kwargs):
        counted.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(FigureCanvasTkAgg, "draw", draw)
    return counted


def _switch(app):
    app.toggle()
    app.root.update()
    app.root.update_idletasks()


# -- the cost --------------------------------------------------------------


#: Renders a plot costs on a switch when the window is the right size first:
#: one for the canvas appearing, one for the figure being drawn into it. Two is
#: the standing cost and is not what this file is about. A *third* is the
#: regression: the window resizing after the plot already existed.
RENDERS_PER_PLOT = 2


def test_a_plot_does_not_render_an_extra_time_per_switch(plots, renders):
    """The regression, stated as a count rather than a stopwatch."""
    _switch(plots)                      # into the editor: no canvases at all
    renders.clear()
    _switch(plots)                      # back to the interface

    assert len(renders) <= 3 * RENDERS_PER_PLOT, (
        f"{len(renders)} canvas renders for 3 plots, over the {3 * RENDERS_PER_PLOT} "
        f"they cost when the window is the right size before they are built - "
        f"the resize landed late and every plot drew again"
    )


def test_leaving_the_interface_renders_nothing(plots, renders):
    """The editor has no canvases, so the direction back costs nothing."""
    renders.clear()
    _switch(plots)
    assert renders == []


def test_the_window_is_the_right_size_before_anything_is_built(plots):
    """What the extra render was paying for. The size has to be real first."""
    sizes = []
    original = plots._construct

    def construct(mode):
        sizes.append((plots.root.winfo_width(), plots.root.winfo_height()))
        return original(mode)

    plots._construct = construct
    _switch(plots)
    assert sizes[-1] == plots._size_for(plots.mode)


# -- and the switch cannot start inside itself -----------------------------


def test_a_second_toggle_during_a_switch_is_refused(plots):
    """Running the event loop mid-switch is what makes this reachable."""
    seen = []
    original = plots._construct

    def construct(mode):
        seen.append(plots.toggle())     # a click arriving mid-rebuild
        return original(mode)

    plots._construct = construct
    _switch(plots)

    assert seen == [plots.mode], "the inner toggle should have changed nothing"
    assert plots.built is not None


def test_the_other_top_bar_actions_are_refused_too(plots):
    """Each one tears down or photographs an interface that is half gone."""
    outcomes = {}
    original = plots._construct

    def construct(mode):
        outcomes["busy"] = plots.busy
        outcomes["rerun"] = plots.rerun_startup()
        outcomes["screenshot"] = plots.save_screenshot()
        return original(mode)

    plots._construct = construct
    _switch(plots)

    assert outcomes["busy"] is True
    assert outcomes["rerun"] is False
    assert outcomes["screenshot"] is None


def test_nothing_is_refused_when_no_switch_is_running(plots):
    """The guard must not leave the top bar dead the rest of the time."""
    assert plots.busy is False
    assert plots.save_screenshot() is not None
