"""Remembering the last file or folder a selector chose.

The memory has to survive a process restart, so it is on disk; it must not be in
the layout file, which describes the interface rather than logging what happened
to it; and it must never be able to break a session, because a read-only profile
or a corrupt file is not the researcher's problem to solve.
"""

import json

import pytest

from iterlab.runtime import remembered


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Never touch the real user state directory from a test."""
    monkeypatch.setattr(remembered, "state_dir", lambda: tmp_path / "iterlab")
    return tmp_path / "iterlab"


@pytest.fixture
def interface(tmp_path):
    path = tmp_path / "project" / "demo.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("schema_version: 5\n", encoding="utf-8")
    return path


# -- the round trip --------------------------------------------------------


def test_nothing_is_remembered_at_first(interface):
    assert remembered.load(interface) == {}


def test_a_selection_survives(interface, tmp_path):
    chosen = tmp_path / "data.csv"
    chosen.write_text("1,2\n", encoding="utf-8")
    assert remembered.remember(interface, "fileselect", str(chosen)) is True
    assert remembered.load(interface) == {"fileselect": str(chosen)}


def test_it_is_stored_outside_the_project(interface, isolated_state, tmp_path):
    """The project stays the two files it has always been."""
    remembered.remember(interface, "fileselect", str(tmp_path / "x.csv"))
    assert (isolated_state / "selections.json").exists()
    assert list(interface.parent.iterdir()) == [interface], "the project folder gained a file"


def test_two_interfaces_do_not_share_a_memory(tmp_path):
    one = tmp_path / "a" / "demo.yaml"
    two = tmp_path / "b" / "demo.yaml"
    for path in (one, two):
        path.parent.mkdir(parents=True)
        path.write_text("schema_version: 5\n", encoding="utf-8")

    remembered.remember(one, "fileselect", "/first")
    remembered.remember(two, "fileselect", "/second")
    assert remembered.load(one)["fileselect"] == "/first"
    assert remembered.load(two)["fileselect"] == "/second"


def test_two_selectors_in_one_interface_are_kept_apart(interface):
    remembered.remember(interface, "fileselect", "/a/file.csv")
    remembered.remember(interface, "folderselect", "/a/dir")
    assert remembered.load(interface) == {
        "fileselect": "/a/file.csv",
        "folderselect": "/a/dir",
    }


def test_the_same_interface_by_a_different_route_is_the_same_memory(interface):
    """`demo.yaml` and `./sub/../demo.yaml` are one interface, not two."""
    remembered.remember(interface, "fileselect", "/x")
    indirect = interface.parent / "." / interface.name
    assert remembered.load(indirect) == {"fileselect": "/x"}


def test_forgetting_removes_it(interface):
    remembered.remember(interface, "fileselect", "/x")
    remembered.forget(interface, "fileselect")
    assert remembered.load(interface) == {}


# -- never a fault ---------------------------------------------------------


def test_a_corrupt_file_reads_as_nothing_remembered(interface, isolated_state):
    isolated_state.mkdir(parents=True, exist_ok=True)
    (isolated_state / "selections.json").write_text("{not json at all", encoding="utf-8")
    assert remembered.load(interface) == {}


def test_a_corrupt_file_is_repaired_by_the_next_write(interface, isolated_state):
    isolated_state.mkdir(parents=True, exist_ok=True)
    (isolated_state / "selections.json").write_text("garbage", encoding="utf-8")
    assert remembered.remember(interface, "fileselect", "/x") is True
    assert remembered.load(interface) == {"fileselect": "/x"}
    json.loads((isolated_state / "selections.json").read_text(encoding="utf-8"))


def test_a_file_of_the_wrong_shape_reads_as_nothing(interface, isolated_state):
    isolated_state.mkdir(parents=True, exist_ok=True)
    (isolated_state / "selections.json").write_text('["a", "list"]', encoding="utf-8")
    assert remembered.load(interface) == {}


def test_a_write_that_fails_costs_the_memory_and_nothing_else(interface, monkeypatch):
    """A read-only profile must not be able to end a session."""
    def refuse(*args, **kwargs):
        raise PermissionError("read-only")

    monkeypatch.setattr("iterlab.codegen.templates.atomic_write", refuse)
    assert remembered.remember(interface, "fileselect", "/x") is False


# -- is the remembered thing still there? ----------------------------------


def test_a_file_that_still_exists_is_usable(tmp_path):
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    assert remembered.usable(str(target)) is True


def test_a_file_that_has_gone_is_not(tmp_path):
    assert remembered.usable(str(tmp_path / "missing.csv")) is False


def test_a_directory_is_not_a_usable_file(tmp_path):
    assert remembered.usable(str(tmp_path)) is False
    assert remembered.usable(str(tmp_path), expect_dir=True) is True


def test_nothing_remembered_is_not_usable():
    assert remembered.usable("") is False


# -- where the dialog opens ------------------------------------------------


def test_it_opens_where_the_remembered_file_is(tmp_path):
    target = tmp_path / "data.csv"
    target.write_text("x", encoding="utf-8")
    assert remembered.starting_directory(str(target)) == str(target)


def test_a_renamed_file_still_offers_its_folder(tmp_path):
    """Usually the file was renamed, not the whole directory thrown away."""
    missing = tmp_path / "gone.csv"
    assert remembered.starting_directory(str(missing)) == str(tmp_path)


def test_a_vanished_folder_falls_back_to_the_working_directory(tmp_path):
    import os

    nowhere = tmp_path / "no" / "such" / "place" / "x.csv"
    assert remembered.starting_directory(str(nowhere)) == os.getcwd()


def test_nothing_remembered_starts_in_the_working_directory():
    import os

    assert remembered.starting_directory("") == os.getcwd()


# -- where the file lives --------------------------------------------------


def test_the_state_directory_is_per_user_not_per_project(monkeypatch):
    monkeypatch.undo()
    path = str(remembered.state_dir())
    assert path.endswith("iterlab")
    assert "AppData" in path or ".local" in path or "Application Support" in path
