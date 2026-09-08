"""`ev.<tag>` for an axes element is a matplotlib `Axes`, not a wrapper.

A wrapper that forwards attributes passes every test that calls a method on it,
which is why those tests are not the interesting ones here. What a wrapper fails
is everything that asks what the object *is* - and it fails it inside whatever
library the researcher passed it to, a long way from anything iterlab wrote.
"""

import pytest
from matplotlib.axes import Axes

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CODE = """
def on_startup(ev):
    ev.ax_0.plot([0, 1, 2], [0, 1, 4])
    ev.ax_0.set_title("drawn")
"""


@pytest.fixture
def gui(make_app):
    app = make_app()
    app.built.create_element("axes", Rect(0.1, 0.1, 0.8, 0.8))
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    return app


def test_the_handle_is_an_instance_of_axes(gui):
    """The whole point. A forwarding wrapper fails exactly here."""
    assert isinstance(gui.built.ev.ax_0, Axes)


def test_matplotlib_accepts_it_where_a_wrapper_would_be_rejected(gui):
    """The reason isinstance matters: other code checks it, and rejects wrappers.

    `Figure.sca` is the check used here rather than `pyplot.sca`, which needs a
    pyplot-managed figure - not something any embedded figure has, wrapper or
    not, so it would prove nothing either way.
    """
    ax = gui.built.ev.ax_0
    assert ax.figure.sca(ax) is ax
    assert ax in ax.figure.axes


def test_ordinary_matplotlib_calls_work(gui):
    ax = gui.built.ev.ax_0
    ax.plot([0, 1], [1, 0], label="line")
    ax.set_xlabel("nm")
    ax.legend()
    assert ax.get_xlabel() == "nm"
    assert ax.get_title() == "drawn"


def test_the_default_tag_is_ax_0(gui):
    assert "ax_0" in gui.interface.layout.tags()


def test_a_second_axes_is_ax_1(gui):
    gui.toggle()
    gui.built.create_element("axes", Rect(0.1, 0.6, 0.3, 0.3))
    assert "ax_1" in gui.interface.layout.tags()


def test_iterlab_additions_do_not_shadow_matplotlib(gui):
    """Everything iterlab adds is prefixed, so nothing can collide."""
    # matplotlib injects names of its own into every Axes subclass (`set`, and
    # bookkeeping like `_subclass_uses_cla`), so a bare subclass is the baseline
    # rather than an empty set.
    class _Probe(Axes):
        pass

    ax = gui.built.ev.ax_0
    ours = set(vars(type(ax))) - set(vars(_Probe))
    intended = {
        "name", "tag", "element", "widget", "canvas", "visible",
        "disconnect", "STYLE_PROPERTIES", "__doc__", "__module__",
        # The element-handle contract every type implements, so that a mode
        # switch can put back what the running interface changed.
        "_presentation", "_restore",
    }
    unexpected = {n for n in ours if not n.startswith("_iterlab_") and n not in intended}
    assert not unexpected, f"unprefixed names added to the Axes subclass: {unexpected}"

    # And nothing we add may shadow something matplotlib already defines.
    shadowed = {n for n in ours if n not in intended and hasattr(_Probe, n)}
    assert not shadowed, f"these shadow matplotlib attributes: {shadowed}"


def test_visible_is_the_element_not_the_artist(gui):
    """Deliberately different from matplotlib's own set_visible.

    `visible` means the same thing on every element type - is this thing on
    screen. matplotlib's `set_visible` hides the axes but leaves the frame and
    toolbar, which is a different question and still answerable.
    """
    ax = gui.built.ev.ax_0
    assert ax.visible is True
    ax.visible = False
    assert ax.visible is False
    assert not ax.widget.winfo_ismapped() or ax.widget.place_info() == {}
    # matplotlib's own notion is untouched
    assert ax.get_visible() is True


def test_the_tag_is_reachable_from_the_axes(gui):
    assert gui.built.ev.ax_0.tag == "ax_0"


def test_the_canvas_follows_the_figure_across_a_switch(gui):
    """`canvas` is derived, not stored, because it changes on every switch."""
    before = gui.built.ev.ax_0.canvas
    gui.toggle()
    gui.toggle()
    after = gui.built.ev.ax_0
    assert after.canvas is not before
    assert after.canvas is after.figure.canvas


def test_a_layout_written_before_the_rename_still_opens(gui):
    """Migration 2 -> 3, through the real file rather than the function."""
    gui.interface.layout_path.write_text(
        "schema_version: 2\n"
        "window: {width: 800, height: 450}\n"
        "elements:\n"
        "  spectrum:\n"
        "    type: plot_area\n"
        "    position: [0.1, 0.1, 0.8, 0.8]\n",
        encoding="utf-8",
    )
    gui.restart_app()
    gui.root.update()
    assert gui.interface.layout.elements["spectrum"].type == "axes"
    assert isinstance(gui.built.ev.spectrum, Axes), "the migrated element is a real Axes"
