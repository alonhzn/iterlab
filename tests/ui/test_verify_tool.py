"""The Gate 2 setup tool still builds what Gate 2 needs.

`tools/verify.py` is the only way a manual pass gets started, and the only thing
that ever runs it is a person about to do one. So when `create_element`'s `name`
argument became `tag`, the tool raised `TypeError` on its first line of work and
stayed broken across releases - the results table in VERIFICATION.md has no row
for any of them, which is what that silence looks like from the outside.

A tool the release process depends on is part of the release process. This runs
it against the same API the application does.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import verify  # noqa: E402

pytestmark = pytest.mark.ui


@pytest.fixture
def scratch(tk_root, tmp_path):
    app = verify.build(tmp_path, _root=tk_root)
    yield app
    app.close()


def test_it_builds_without_raising(scratch):
    """The defect itself: it raised on the first element."""
    assert scratch.built is not None


def test_every_declared_element_is_there(scratch):
    tags = set(scratch.interface.layout.elements)
    assert tags == {tag for _type, _rect, tag, _label in verify.ELEMENTS}


def test_the_research_code_is_the_one_written_for_the_pass(scratch):
    source = scratch.interface.code_path.read_text(encoding="utf-8")
    assert source == verify.RESEARCH_CODE


def test_the_code_reaches_for_tags_that_exist(scratch):
    """A handler naming an element nobody drew would fail mid-pass."""
    source = scratch.interface.code_path.read_text(encoding="utf-8")
    for tag in scratch.interface.layout.elements:
        assert f"ev.{tag}" in source or f"on_clicked_{tag}" in source, tag


def test_the_handlers_match_the_buttons(scratch):
    source = scratch.interface.code_path.read_text(encoding="utf-8")
    for element_type, _rect, tag, _label in verify.ELEMENTS:
        if element_type == "button":
            assert f"def on_clicked_{tag}(" in source, tag


def test_the_research_code_parses(scratch):
    compile(verify.RESEARCH_CODE, "verify.py", "exec")


def test_the_buttons_say_what_the_checklist_calls_them(scratch):
    """The checklist says "click Redraw". Something has to say Redraw.

    Buttons gained a default label of "Click here!" after this tool was written,
    so both of them read the same thing and neither read as the one the
    instructions name.
    """
    checklist = (Path(__file__).resolve().parents[2] / "VERIFICATION.md").read_text(
        encoding="utf-8"
    )
    for element_type, _rect, tag, label in verify.ELEMENTS:
        if element_type != "button":
            continue
        drawn = scratch.interface.layout.elements[tag].label
        assert drawn == label, f"{tag} is labelled {drawn!r}"
        assert label in checklist, f"nothing in the checklist mentions {label!r}"


def test_the_two_buttons_can_be_told_apart(scratch):
    labels = [
        scratch.interface.layout.elements[tag].label
        for element_type, _rect, tag, _label in verify.ELEMENTS
        if element_type == "button"
    ]
    assert len(set(labels)) == len(labels), labels
