"""Crossing between iterlab versions copies the project aside first.

Every layout records which iterlab last wrote it. When that differs from the one
opening it — in either direction — both files are copied before anything touches
them, because a version change is the one moment a file can be rewritten by code
that was never run against it.

The downgrade is the dangerous direction: an older build meets a key or a type it
has never heard of. An upgrade is safer, since migrations run forward and are
tested, but a migration is still a rewrite of the researcher's layout.
"""

import pytest

import iterlab
from iterlab.app import guard_version
from iterlab.interface import Interface
from iterlab.layout import store
from iterlab.layout.schema import Element, Rect
from iterlab.versionguard import UNKNOWN, backup_path, needs_backup

CODE = "def on_startup(ev):\n    ev.data = list(range(100))\n"


@pytest.fixture
def interface(tmp_path):
    made = Interface(name="demo", directory=tmp_path)
    made.ensure_files()
    made.load_layout()
    made.layout.add(Element("cmd_0", "button", Rect(0.1, 0.1, 0.2, 0.05), label="Go"))
    made.save_layout()
    made.code_path.write_text(CODE, encoding="utf-8")
    made.load_layout()
    return made


def _stamp_as(interface, version):
    """Rewrite the file as though `version` had been the one to save it."""
    text = interface.layout_path.read_text(encoding="utf-8")
    text = text.replace(f"iterlab_version: {iterlab.__version__}", f"iterlab_version: {version}")
    interface.layout_path.write_text(text, encoding="utf-8")
    interface.load_layout()


def _backups(interface):
    return sorted(p.name for p in interface.dir.glob("*.bak"))


# -- the decision ----------------------------------------------------------


def test_the_same_version_needs_nothing():
    assert needs_backup("1.4.0", "1.4.0") is False


@pytest.mark.parametrize("recorded", ["1.2.0", "2.0.0", "1.4.1"])
def test_any_difference_needs_a_backup(recorded):
    """Not "older than": either direction is a difference."""
    assert needs_backup(recorded, "1.4.0") is True


def test_an_unstamped_file_needs_one():
    """Written before this existed, so nothing is known about it."""
    assert needs_backup("", "1.4.0") is True


# -- the names -------------------------------------------------------------


def test_the_name_matches_the_requested_shape(tmp_path):
    assert backup_path(tmp_path / "demo.yaml", "1.2.0").name == "demo.yaml.v1.2.0.bak"
    assert backup_path(tmp_path / "demo.py", "1.2.0").name == "demo.py.v1.2.0.bak"


def test_the_name_carries_the_version_that_wrote_it(tmp_path):
    """Not the version opening it: the copy is of what *that* version left."""
    assert "v1.2.0" in backup_path(tmp_path / "demo.yaml", "1.2.0").name


def test_an_unstamped_file_is_not_given_a_fake_version(tmp_path):
    name = backup_path(tmp_path / "demo.yaml", "").name
    assert UNKNOWN in name
    assert name == f"demo.yaml.v{UNKNOWN}.bak"


# -- what actually happens on open -----------------------------------------


def test_nothing_is_copied_when_the_version_matches(interface):
    guard_version(interface)
    assert _backups(interface) == []


def test_both_files_are_copied_on_a_difference(interface):
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    assert _backups(interface) == ["demo.py.v1.2.0.bak", "demo.yaml.v1.2.0.bak"]


def test_a_downgrade_is_copied_too(interface):
    """The dangerous direction, and the reason this is not a "newer than" test."""
    _stamp_as(interface, "9.9.9")
    guard_version(interface)
    assert _backups(interface) == ["demo.py.v9.9.9.bak", "demo.yaml.v9.9.9.bak"]


def test_the_copy_holds_what_that_version_left(interface):
    """The whole point: the copy is the file *before* anything rewrote it."""
    original_layout = interface.layout_path.read_bytes()
    _stamp_as(interface, "1.2.0")
    before = interface.layout_path.read_bytes()

    guard_version(interface)
    interface.save_layout()          # the rewrite the backup exists to survive

    copy = interface.dir / "demo.yaml.v1.2.0.bak"
    assert copy.read_bytes() == before
    assert copy.read_bytes() != interface.layout_path.read_bytes()
    assert original_layout != before  # the fixture really did change the stamp


def test_the_code_file_is_copied_byte_for_byte(interface):
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    assert (interface.dir / "demo.py.v1.2.0.bak").read_text(encoding="utf-8") == CODE


def test_the_code_file_itself_is_not_touched(interface):
    """This copies the researcher's code. It never writes to it."""
    _stamp_as(interface, "1.2.0")
    before = interface.code_path.read_bytes()
    guard_version(interface)
    assert interface.code_path.read_bytes() == before


def test_an_existing_backup_is_not_overwritten(interface):
    """Crossing the same boundary twice must not replace the earlier copy.

    The one already on disk is the older and more original of the two.
    """
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    copy = interface.dir / "demo.yaml.v1.2.0.bak"
    first = copy.read_bytes()

    interface.layout_path.write_text("schema_version: 6\nelements: {}\n", encoding="utf-8")
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    assert copy.read_bytes() == first


def test_saving_stamps_the_version_that_saved(interface):
    _stamp_as(interface, "1.2.0")
    assert interface.layout.iterlab_version == "1.2.0"
    interface.save_layout()
    assert store.load(interface.layout_path).iterlab_version == iterlab.__version__


def test_crossing_once_does_not_keep_crossing(interface):
    """After the stamp is refreshed, reopening is an ordinary open."""
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    interface.save_layout()
    interface.load_layout()

    for stray in interface.dir.glob("*.bak"):
        stray.unlink()
    guard_version(interface)
    assert _backups(interface) == []


def test_a_folder_that_cannot_be_written_does_not_stop_the_open(interface, monkeypatch):
    """A read-only folder is one iterlab cannot damage either."""
    import shutil

    def refuse(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(shutil, "copy2", refuse)
    _stamp_as(interface, "1.2.0")
    assert guard_version(interface) == []
    assert _backups(interface) == []


def test_the_researcher_is_told(interface, capsys):
    """A guard that runs silently is one nobody knows ran."""
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    printed = capsys.readouterr().out
    assert "1.2.0" in printed
    assert iterlab.__version__ in printed
    assert "demo.yaml.v1.2.0.bak" in printed


def test_an_unstamped_project_is_announced_too(interface, capsys):
    """The commonest crossing of all, and it used to happen in silence.

    Every project made before this feature has no stamp, so an early return on
    "no recorded version" meant the one case everybody would hit was the one
    nobody was told about.
    """
    text = interface.layout_path.read_text(encoding="utf-8")
    kept = [l for l in text.splitlines() if not l.startswith("iterlab_version:")]
    interface.layout_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    interface.load_layout()

    guard_version(interface)
    printed = capsys.readouterr().out
    assert f"demo.yaml.v{UNKNOWN}.bak" in printed
    assert "older than" in printed
    assert _backups(interface) == [
        f"demo.py.v{UNKNOWN}.bak", f"demo.yaml.v{UNKNOWN}.bak"
    ]


def test_a_failed_backup_is_not_reported_as_a_success(interface, capsys, monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "copy2", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    _stamp_as(interface, "1.2.0")
    guard_version(interface)
    printed = capsys.readouterr().out
    assert "No new backups" in printed
