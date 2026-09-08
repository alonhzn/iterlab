"""Generated text. The signature is public surface; the comments are not."""

import ast

from iterlab.codegen import templates
from iterlab.layout.schema import Element, Rect


def _element(name, type_):
    return Element(name, type_, Rect(0.1, 0.1, 0.3, 0.3))


def test_starter_file_parses_and_defines_on_startup():
    tree = ast.parse(templates.starter_file("demo"))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["on_startup"]


def test_starter_file_steers_data_loading_into_startup():
    """The mitigation for the one accepted limitation (research.md R3).

    Reloading a module re-executes its top level, so data loaded there reloads
    on every edit. The only defense is making the safe path the obvious one.
    """
    text = templates.starter_file("demo")
    assert "not at the top of this file" in text
    assert "re-runs when iterlab picks up an edit" in text


def test_starter_file_shows_the_single_command():
    text = templates.starter_file("demo")
    assert "iterlab demo" in text
    assert "iterlab run demo" not in text
    assert "iterlab edit demo" not in text


def test_stub_signature_matches_the_contract():
    for type_ in ("button", "plot_area"):
        tree = ast.parse(templates.default_stub(_element("thing", type_)))
        fn = tree.body[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "on_clicked_thing"
        assert [a.arg for a in fn.args.args] == ["ev", "event"]


def test_exactly_one_stub_per_element():
    tree = ast.parse(templates.default_stub(_element("run_fit", "button")))
    assert len([n for n in tree.body if isinstance(n, ast.FunctionDef)]) == 1


def test_no_stub_for_non_default_interactions():
    """Only the default interaction is generated (FR-017d)."""
    text = templates.default_stub(_element("run_fit", "button"))
    assert "on_hover_" not in text
    assert "on_motion_" not in text
    assert "on_key_" not in text


def test_plot_stub_mentions_data_coordinates():
    text = templates.default_stub(_element("spectrum", "plot_area"))
    assert "data coordinates" in text


def test_stub_tells_the_researcher_they_may_delete_it():
    text = templates.default_stub(_element("run_fit", "button"))
    assert "Delete this function" in text


def test_atomic_write_leaves_no_temp_files(tmp_path):
    target = tmp_path / "demo.py"
    templates.atomic_write(target, "x = 1\n")
    assert [p.name for p in tmp_path.iterdir()] == ["demo.py"]
    assert target.read_text(encoding="utf-8") == "x = 1\n"
