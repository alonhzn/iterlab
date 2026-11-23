"""The list element, running: what code can do to it and what a click reports."""

import time

import pytest

from iterlab.layout.schema import Rect

pytestmark = pytest.mark.ui

CODE = """
def on_startup(ev):
    ev.got = []

def on_clicked_lst_0(ev, event):
    ev.got.append(("clicked", event.index, event.text, event.button, event.key, event.double))

def on_key_lst_0(ev, event):
    ev.got.append(("key", event.index, event.key))

def on_motion_lst_0(ev, event):
    ev.got.append(("motion", event.index, event.text))
"""


def _make(make_app, **options):
    app = make_app()
    d = app.built
    d.create_element("list", Rect(0.1, 0.1, 0.5, 0.8), tag="lst_0")
    if options:
        app.interface.layout.set_list_options("lst_0", **options)
        app.interface.save_layout()
    app.interface.code_path.write_text(CODE, encoding="utf-8")
    app.toggle()
    app.root.geometry("800x500")
    app.root.update()
    return app


@pytest.fixture
def gui(mapped, make_app):
    return _make(make_app)


@pytest.fixture
def multi(mapped, make_app):
    return _make(make_app, multi_select=True)


def _lst(app):
    return app.built.handles["lst_0"]


def _got(app):
    return app.built.ev.got


def _shown(app):
    """What the widget actually displays, row by row."""
    return _lst(app)._text.get("1.0", "end-1c").split("\n")[:-1]


def _click(app, index, sequence="<Button-1>"):
    text = _lst(app)._text
    app.root.update()
    x, y, _w, h, _b = text.dlineinfo(f"{index + 1}.0")
    text.event_generate(sequence, x=x + 5, y=y + h // 2)
    app.root.update()


def _row_tags(app, index):
    return _lst(app)._text.tag_names(f"{index + 1}.0")


def _picked(app):
    """Which rows are drawn selected - per row, since Tk merges adjacent ranges."""
    return [i for i in range(_lst(app).length) if "picked" in _row_tags(app, i)]


# -- filling it --------------------------------------------------------------


def test_it_starts_empty(gui):
    assert _lst(gui).length == 0 and len(_lst(gui)) == 0
    assert _lst(gui).selected is None


def test_rows_are_added_at_the_bottom(gui):
    lst = _lst(gui)
    lst.append("one")
    lst.append("two")
    assert lst.lines == ("one", "two") and lst.length == 2
    assert _shown(gui) == ["one", "two"]


def test_insert_puts_a_row_anywhere(gui):
    lst = _lst(gui)
    lst.extend(["a", "c"])
    lst.insert(1, "b")
    lst.insert(0, "start")
    lst.insert(lst.length, "end")
    assert lst.lines == ("start", "a", "b", "c", "end")
    assert _shown(gui) == list(lst.lines)


def test_reading_rows(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    assert (lst[0], lst[-1]) == ("a", "c")
    assert lst[1:] == ["b", "c"]
    assert list(lst) == ["a", "b", "c"]


def test_deleting_closes_the_gap(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c", "d"])
    del lst[1]
    assert lst.lines == ("a", "c", "d") and lst[1] == "c"
    lst.delete(-1)
    assert lst.lines == ("a", "c")
    assert _shown(gui) == ["a", "c"]


def test_deleting_a_slice(gui):
    lst = _lst(gui)
    lst.extend("abcdef")
    del lst[1:4]
    assert lst.lines == ("a", "e", "f") and _shown(gui) == ["a", "e", "f"]


def test_replacing_a_rows_text(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst[1] = "B"
    assert lst.lines == ("a", "B") and _shown(gui) == ["a", "B"]


def test_anything_becomes_text(gui):
    lst = _lst(gui)
    lst.append(3.5)
    lst.insert(0, None)
    assert lst.lines == ("None", "3.5")


def test_clear(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.selected = 0
    lst.clear()
    assert lst.length == 0 and _shown(gui) == [] and lst.selected is None


def test_there_are_no_holes(gui):
    lst = _lst(gui)
    lst.append("a")
    with pytest.raises(IndexError):
        lst.insert(3, "far away")
    with pytest.raises(IndexError):
        lst[5]
    with pytest.raises(IndexError):
        del lst[1]
    with pytest.raises(TypeError):
        lst["0"]


def test_an_empty_list_is_still_an_element(gui):
    """`if handle:` inside iterlab must not take an empty list for no list."""
    assert bool(_lst(gui)) is True


# -- how rows look -----------------------------------------------------------


def test_style_line_sets_one_rows_look(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    lst.style_line(1, text_color="#ff0000", highlight="#fff4d6", bold=True, font_size=14)
    tag = lst._rows[1].tag
    text = lst._text
    assert text.tag_cget(tag, "foreground") == "#ff0000"
    assert text.tag_cget(tag, "background") == "#fff4d6"
    assert "bold" in str(text.tag_cget(tag, "font")) and "14" in str(text.tag_cget(tag, "font"))
    assert tag in _row_tags(gui, 1)
    assert lst._rows[0].tag not in _row_tags(gui, 1)


def test_a_rows_style_moves_with_it(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "red"])
    lst.style_line(2, text_color="#ff0000")
    del lst[0]
    assert lst[1] == "red"
    assert _lst(gui)._text.tag_cget(lst._rows[1].tag, "foreground") == "#ff0000"
    assert lst._rows[1].tag in _row_tags(gui, 1)
    lst.insert(0, "new")
    assert lst._rows[2].tag in _row_tags(gui, 2) and lst[2] == "red"


def test_replacing_text_keeps_the_style(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.style_line(1, bold=True)
    lst[1] = "B"
    assert lst._rows[1].tag in _row_tags(gui, 1)


def test_none_puts_a_property_back(gui):
    lst = _lst(gui)
    lst.append("a")
    lst.style_line(0, text_color="#ff0000", bold=True)
    lst.style_line(0, text_color=None)
    assert lst._rows[0].style == {"bold": True}


def test_style_line_refuses_what_it_cannot_do(gui):
    lst = _lst(gui)
    lst.append("a")
    with pytest.raises(TypeError, match="align"):
        lst.style_line(0, align="left")
    with pytest.raises(ValueError):
        lst.style_line(0, text_color="nope!")
    assert lst._rows[0].style == {}


def test_the_lists_own_style_reaches_every_row(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.highlight = "#e0f0ff"
    assert lst._text.tag_cget("line", "background") == "#e0f0ff"
    lst.font_size = 16
    assert "16" in str(lst._text.cget("font"))


def test_a_rows_font_follows_the_lists_size_unless_it_set_one(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.style_line(0, bold=True)
    lst.font_size = 18
    assert "18" in str(lst._text.tag_cget(lst._rows[0].tag, "font"))


# -- clicking ----------------------------------------------------------------


def test_a_click_reports_the_row_and_its_text(gui):
    _lst(gui).extend(["alpha", "beta", "gamma"])
    _click(gui, 1)
    assert _got(gui) == [("clicked", 1, "beta", "left", None, False)]


def test_a_click_selects_and_highlights_the_row(gui):
    _lst(gui).extend(["a", "b", "c"])
    _click(gui, 2)
    assert _lst(gui).selected == 2 and _picked(gui) == [2]
    _click(gui, 0)
    assert _lst(gui).selected == 0 and _picked(gui) == [0]


def test_clicking_below_the_last_row_does_nothing(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.selected = 1
    text = lst._text
    gui.root.update()
    text.event_generate("<Button-1>", x=10, y=text.winfo_height() - 5)
    gui.root.update()
    assert _got(gui) == [] and lst.selected == 1


def test_a_double_click_says_so(gui):
    _lst(gui).extend(["a", "b"])
    # Tk refuses to synthesise <Double-...>; two presses in a row are one.
    text = _lst(gui)._text
    x, y, _w, h, _b = text.dlineinfo("2.0")
    for sequence in ("<Button-1>", "<ButtonRelease-1>", "<Button-1>"):
        text.event_generate(sequence, x=x + 5, y=y + h // 2)
    gui.root.update()
    assert _got(gui)[-1] == ("clicked", 1, "b", "left", None, True)


def test_a_right_click_reports_without_selecting(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.selected = 0
    _click(gui, 1, "<ButtonRelease-3>")
    assert _got(gui) == [("clicked", 1, "b", "right", None, False)]
    assert lst.selected == 0


def test_the_selection_follows_its_row(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    _click(gui, 2)
    del lst[0]
    assert lst.selected == 1 and _picked(gui) == [1]
    del lst[1]
    assert lst.selected is None


def test_selecting_from_code(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    lst.selected = -1
    assert lst.selected == 2 and _picked(gui) == [2]
    lst.selected = None
    assert lst.selected is None and _picked(gui) == []
    with pytest.raises(ValueError):
        lst.selected = (0, 1)
    with pytest.raises(IndexError):
        lst.selected = 7
    assert _got(gui) == [], "selecting from code is not a click"


def test_the_arrows_move_the_selection(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    _click(gui, 0)
    # A click focuses the list on a real desktop. A virtual display has no
    # window manager to give the window the keyboard, so take it explicitly.
    lst._text.focus_force()
    gui.root.update()
    lst._text.event_generate("<Down>")
    gui.root.update()
    assert lst.selected == 1
    assert ("clicked", 1, "b", None, "Down", False) in _got(gui)
    assert ("key", 1, "Down") in _got(gui)
    lst._text.event_generate("<Up>")
    lst._text.event_generate("<Up>")
    gui.root.update()
    assert lst.selected == 0, "stops at the top"


def test_motion_reports_the_row_under_the_pointer(gui):
    _lst(gui).extend(["a", "b"])
    _click(gui, 1, "<Motion>")
    assert ("motion", 1, "b") in _got(gui)


def test_a_disabled_list_ignores_clicks(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    lst.enabled = False
    _click(gui, 1)
    assert _got(gui) == [] and lst.selected is None


# -- selecting several -------------------------------------------------------

ADD, REMOVE = ("<Control-Button-1>", "<Alt-Button-1>")


@pytest.fixture
def keys(multi):
    if multi.root.tk.call("tk", "windowingsystem") == "aqua":
        return "<Command-Button-1>", "<Option-Button-1>"
    return ADD, REMOVE


def test_multi_select_adds_and_removes(multi, keys):
    add, remove = keys
    lst = _lst(multi)
    lst.extend("abcde")
    assert lst.selected == ()
    _click(multi, 1)
    _click(multi, 3, add)
    _click(multi, 4, add)
    assert lst.selected == (1, 3, 4) and _picked(multi) == [1, 3, 4]
    _click(multi, 3, remove)
    assert lst.selected == (1, 4)
    _click(multi, 2)
    assert lst.selected == (2,), "a plain click starts again"
    assert len(_got(multi)) == 5, "every click reaches the handler"


def test_multi_selection_from_code(multi):
    lst = _lst(multi)
    lst.extend("abc")
    lst.selected = (2, 0)
    assert lst.selected == (0, 2)
    lst.selected = 1
    assert lst.selected == (1,)


def test_without_multi_select_the_modifiers_just_select(gui):
    lst = _lst(gui)
    lst.extend("abc")
    _click(gui, 0)
    _click(gui, 2, ADD)
    assert lst.selected == 2


# -- long lists and long lines -----------------------------------------------


def test_a_scrollbar_appears_only_when_rows_overflow(gui):
    lst = _lst(gui)
    lst.extend(["a", "b"])
    gui.root.update()
    bars = [w for w in lst.widget.winfo_children() if w.winfo_class() == "TScrollbar"]
    vertical = next(b for b in bars if str(b.cget("orient")) == "vertical")
    assert not vertical.winfo_ismapped()
    lst.extend(str(i) for i in range(200))
    gui.root.update()
    assert vertical.winfo_ismapped()


def test_appending_follows_the_bottom(gui):
    lst = _lst(gui)
    lst.extend(str(i) for i in range(300))
    gui.root.update()
    assert lst._text.yview()[1] == 1.0
    lst.append("newest")
    gui.root.update()
    assert lst._text.yview()[1] == 1.0, "a new row at the bottom is shown"


def test_appending_leaves_you_where_you_were_reading(gui):
    lst = _lst(gui)
    lst.extend(str(i) for i in range(300))
    lst._text.yview_moveto(0.0)
    gui.root.update()
    lst.append("newest")
    gui.root.update()
    assert lst._text.yview()[0] == 0.0


def test_long_lines_are_cut_off_by_default(gui):
    lst = _lst(gui)
    lst.append("x" * 2000)
    gui.root.update()
    text = lst._text
    text.focus_force()
    gui.root.update()
    for sequence in ("<Right>", "<Shift-MouseWheel>"):
        text.event_generate(sequence, delta=-120) if "Wheel" in sequence else text.event_generate(sequence)
    gui.root.update()
    assert text.xview()[0] == 0.0
    bars = [w for w in lst.widget.winfo_children() if w.winfo_ismapped()]
    assert all(str(b.cget("orient")) != "horizontal" for b in bars if b.winfo_class() == "TScrollbar")


def test_scroll_sideways_shows_a_scrollbar_for_a_long_line(mapped, make_app):
    app = _make(make_app, scroll_x=True)
    lst = _lst(app)
    lst.append("x" * 2000)
    app.root.update()
    bars = [w for w in lst.widget.winfo_children()
            if w.winfo_class() == "TScrollbar" and str(w.cget("orient")) == "horizontal"]
    assert bars and bars[0].winfo_ismapped()
    lst._text.focus_force()
    app.root.update()
    lst._text.event_generate("<Right>")
    app.root.update()
    assert lst._text.xview()[0] > 0.0


def test_thousands_of_rows_stay_quick(gui):
    lst = _lst(gui)
    start = time.perf_counter()
    for i in range(5000):
        lst.append(f"row {i}")
    gui.root.update()
    one_by_one = time.perf_counter() - start
    assert lst.length == 5000
    assert one_by_one < 3.0, f"5000 appends took {one_by_one:.2f}s"
    start = time.perf_counter()
    lst.style_line(4000, bold=True)
    del lst[10]
    lst.selected = 4500
    assert time.perf_counter() - start < 0.5


# -- surviving -----------------------------------------------------------------


def test_rows_styles_and_selection_survive_a_trip_to_the_editor(gui):
    lst = _lst(gui)
    lst.extend(["a", "b", "c"])
    lst.style_line(1, text_color="#ff0000")
    lst.selected = 2
    gui.toggle()
    gui.toggle()
    gui.root.update()
    lst = _lst(gui)
    assert lst.lines == ("a", "b", "c") and lst.selected == 2
    assert lst._text.tag_cget(lst._rows[1].tag, "foreground") == "#ff0000"
    assert _shown(gui) == ["a", "b", "c"]


def test_turning_multi_select_off_keeps_one_selected_row(multi):
    lst = _lst(multi)
    lst.extend("abc")
    lst.selected = (0, 2)
    multi.toggle()
    multi.interface.layout.set_list_options("lst_0", multi_select=False)
    multi.toggle()
    multi.root.update()
    assert _lst(multi).selected == 0


def test_a_hard_reset_empties_it(gui):
    _lst(gui).extend(["a", "b"])
    gui.restart_app()
    gui.root.update()
    assert _lst(gui).length == 0
