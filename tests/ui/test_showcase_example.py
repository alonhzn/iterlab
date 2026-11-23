"""The showcase project in `examples/` still opens and still draws.

A curated project is code that nobody runs until someone runs it. `tools/
verify.py` proved how that ends: it called `create_element(name=...)` for
several releases after the argument became `tag`, and the only person who would
have noticed was the one it stopped from doing a manual pass.

This one is worse placed to rot quietly, because it is what a screenshot in the
README shows. So the suite opens it, runs its startup, and uses its controls.

Opened from a copy in a temporary directory, so a test can never write to the
project that ships.
"""

import shutil
from pathlib import Path

import pytest

from iterlab.app import open_interface

pytestmark = pytest.mark.ui

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture(scope="module")
def opened(tk_root, tmp_path_factory):
    """One app for the whole file, from a copy of the shipped pair.

    Module-scoped on purpose. Every app built on the shared root leaves three
    figure canvases and three matplotlib toolbars behind it, and enough of them
    take the Tcl interpreter down in some unrelated test several files later -
    an access violation while building an ordinary label, hundreds of tests
    after the one that caused it. One app costs nothing in coverage here,
    because what is under test is the project, not the building of it.

    A copy, so no test can ever write to the project that ships.
    """
    work = tmp_path_factory.mktemp("showcase")
    for name in ("showcase.py", "showcase_layout.py"):
        shutil.copy2(EXAMPLES / name, work / name)

    tk_root.deiconify()
    app = open_interface(str(work / "showcase"), _show=False, _root=tk_root)
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
def showcase(opened):
    """The shared app, put back the way it started.

    Through the Reset button rather than by rebuilding, so a test that leaves a
    control somewhere odd cannot leak into the next one - and Reset is exercised
    on every test rather than only its own.
    """
    opened.built.handles["cmd_reset"].widget.invoke()
    opened.root.update()
    return opened


def _commit(app, tag, text):
    """Type into a box and commit it, the way a researcher would."""
    widget = app.built.handles[tag].widget
    widget.focus_force()
    widget.update()
    widget.delete(0, "end")
    widget.insert(0, text)
    widget.event_generate("<Return>", when="now")
    app.root.update()


# -- it opens ready to use -------------------------------------------------


def test_it_opens_in_gui_mode(showcase):
    """It has elements, so it opens as something to use, not to draw."""
    assert showcase.mode == "gui"


def test_no_fault_on_opening(showcase):
    assert showcase.built.banner.visible is False


def test_startup_drew_every_plot(showcase):
    ev = showcase.built.ev
    assert len(ev.ax_waves.lines) == 3, "one line per default frequency"
    assert len(ev.ax_bars.patches) == 5, "one bar per region"
    assert len(ev.ax_scatter.collections) == 1, "the scatter cloud"


def test_the_status_line_says_what_was_drawn(showcase):
    assert showcase.built.ev.lbl_status.text == "3 sines, 240 samples, noise 0.25"


# -- and the controls do something -----------------------------------------


def test_editing_the_frequencies_changes_the_plot(showcase):
    _commit(showcase, "edt_freq", "0.5, 1, 2, 3, 5")
    assert len(showcase.built.ev.ax_waves.lines) == 5


def test_a_single_frequency_reads_as_singular(showcase):
    _commit(showcase, "edt_freq", "2")
    assert showcase.built.ev.lbl_status.text.startswith("1 sine,")


def test_unparseable_input_falls_back_rather_than_failing(showcase):
    """Half-typed input is normal in a box someone is typing into."""
    _commit(showcase, "edt_freq", "nonsense")
    assert len(showcase.built.ev.ax_waves.lines) == 1
    assert showcase.built.banner.visible is False


def test_shuffle_moves_the_data(showcase):
    before = list(showcase.built.ev.reading)
    showcase.built.handles["cmd_shuffle"].widget.invoke()
    showcase.root.update()
    assert list(showcase.built.ev.reading) != before


def test_reset_puts_the_defaults_back(showcase):
    _commit(showcase, "edt_freq", "9")
    _commit(showcase, "val_points", "17")
    assert showcase.built.ev.lbl_status.text != "3 sines, 240 samples, noise 0.25"

    showcase.built.handles["cmd_reset"].widget.invoke()
    showcase.root.update()
    assert showcase.built.ev.lbl_status.text == "3 sines, 240 samples, noise 0.25"
    assert showcase.built.ev.edt_freq.text == "1, 2.5, 4"


def test_redraw_never_reloads_the_session(showcase):
    """The paradigm's claim: a button redraws, it does not start over."""
    ev = showcase.built.ev
    marker = object()
    ev.marker = marker
    showcase.built.handles["cmd_redraw"].widget.invoke()
    showcase.root.update()
    assert showcase.built.ev.marker is marker


# -- and it is a project, not a special case -------------------------------


def test_every_handler_it_declares_matches_an_element(showcase):
    """A handler for a tag nobody drew is dead code that looks alive."""
    import ast

    source = showcase.interface.code_path.read_text(encoding="utf-8")
    tags = set(showcase.interface.layout.elements)
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for prefix in ("on_clicked_", "on_changed_"):
            if node.name.startswith(prefix):
                assert node.name[len(prefix):] in tags, node.name


def test_the_shipped_layout_records_the_current_version():
    """Otherwise every researcher who opens it is told it is from elsewhere.

    A layout carries the version that last wrote it, and opening one written by
    a different iterlab copies both files aside first. The example shipped with
    1.5.0 stamped 1.4.0, so the first thing it did for anybody was announce a
    version crossing and leave two `.bak` files beside itself.

    It goes stale on every release, which is exactly why a test holds it.
    """
    import iterlab
    from iterlab.layout import store

    layout = store.load(EXAMPLES / "showcase_layout.py")
    assert layout.iterlab_version == iterlab.__version__


# -- the list of regions ---------------------------------------------------

BAR, DIMMED = "#2f6feb", "#c4cad2"


def _click_row(app, index, sequence="<Button-1>"):
    text = app.built.handles["lst_regions"]._text
    app.root.update()
    x, y, _w, h, _b = text.dlineinfo(f"{index + 1}.0")
    text.event_generate(sequence, x=x + 5, y=y + h // 2)
    app.root.update()


def _bar_colours(app):
    from matplotlib.colors import to_hex

    return [to_hex(bar.get_facecolor(), keep_alpha=False) for bar in app.built.ev.ax_bars.patches]


def test_startup_lists_every_region_with_its_reading(showcase):
    ev = showcase.built.ev
    assert ev.lst_regions.length == 5
    assert ev.lst_regions[0].startswith("north")
    assert f"{ev.reading[0]:.2f}" in ev.lst_regions[0]


def test_the_best_and_worst_regions_are_marked(showcase):
    import numpy as np

    lst = showcase.built.ev.lst_regions
    best, worst = int(np.argmax(showcase.built.ev.reading)), int(np.argmin(showcase.built.ev.reading))
    assert lst._rows[best].style == {"text_color": "#1a7f37", "bold": True}
    assert lst._rows[worst].style == {"text_color": "#b42318", "highlight": "#fde8e8"}
    others = [r.style for i, r in enumerate(lst._rows) if i not in (best, worst)]
    assert all(style == {} for style in others)


def test_clicking_regions_picks_their_bars(showcase):
    _click_row(showcase, 1)
    add = "<Command-Button-1>" if showcase.root.tk.call("tk", "windowingsystem") == "aqua" else "<Control-Button-1>"
    _click_row(showcase, 3, add)
    assert showcase.built.ev.lst_regions.selected == (1, 3)
    colours = _bar_colours(showcase)
    assert [i for i, c in enumerate(colours) if c == BAR] == [1, 3]
    assert [i for i, c in enumerate(colours) if c == DIMMED] == [0, 2, 4]
    assert "east, west" in showcase.built.ev.ax_bars.get_title(loc="left")


def test_shuffle_keeps_the_picked_regions_and_moves_the_marks(showcase):
    import numpy as np

    showcase.built.ev.lst_regions.selected = (2,)
    for _ in range(3):
        showcase.built.handles["cmd_shuffle"].widget.invoke()
        showcase.root.update()
        lst = showcase.built.ev.lst_regions
        assert lst.selected == (2,)
        assert lst._rows[int(np.argmax(showcase.built.ev.reading))].style.get("bold")
        assert sum(bool(r.style) for r in lst._rows) == 2


def test_reset_clears_the_picked_regions(showcase):
    _click_row(showcase, 0)
    showcase.built.handles["cmd_reset"].widget.invoke()
    showcase.root.update()
    assert showcase.built.ev.lst_regions.selected == ()
    assert set(_bar_colours(showcase)) == {BAR}, "nothing picked: every bar in full colour"
