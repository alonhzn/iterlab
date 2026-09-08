"""Name resolution and exit codes (contracts/commands.md)."""

import pytest

from iterlab.cli import EXIT_NO_TKINTER, EXIT_USAGE, build_parser, main
from iterlab.interface import Interface


def test_bare_name_resolves_to_cwd_pair(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    i = Interface.resolve("demo")
    assert i.name == "demo"
    assert i.layout_path == tmp_path.resolve() / "demo.yaml"
    assert i.code_path == tmp_path.resolve() / "demo.py"


def test_relative_path_resolves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "work").mkdir()
    i = Interface.resolve("work/demo")
    assert i.layout_path == tmp_path.resolve() / "work" / "demo.yaml"


def test_absolute_path_resolves(tmp_path):
    i = Interface.resolve(str(tmp_path / "demo"))
    assert i.layout_path == tmp_path.resolve() / "demo.yaml"


@pytest.mark.parametrize("given", ["demo.yaml", "demo.py", "demo.yml"])
def test_either_file_of_the_pair_may_be_named(tmp_path, monkeypatch, given):
    """A researcher with the file open in an editor will tab-complete one."""
    monkeypatch.chdir(tmp_path)
    i = Interface.resolve(given)
    assert i.name == "demo"
    assert i.layout_path.name == "demo.yaml"
    assert i.code_path.name == "demo.py"


def test_resolution_is_anchored_to_the_pair_not_the_cwd(tmp_path, monkeypatch):
    """FR-035: launching from elsewhere must not break an interface."""
    project = tmp_path / "project"
    project.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    monkeypatch.chdir(elsewhere)
    i = Interface.resolve(str(project / "demo"))
    i.ensure_files()

    monkeypatch.chdir(tmp_path)
    assert i.layout_path.exists()
    assert i.layout_path.parent == project.resolve()


def test_parser_takes_one_positional_and_no_subcommand():
    parser = build_parser()
    args = parser.parse_args(["demo"])
    assert args.name == "demo"
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_missing_tkinter_exits_three_with_an_actionable_message(monkeypatch, capsys):
    """R12: never a bare ModuleNotFoundError."""
    from iterlab.ui import app as ui_app

    def explode(name):
        raise ui_app.TkinterMissing()

    monkeypatch.setattr("iterlab.app.open_interface", explode)
    code = main(["demo"])
    assert code == EXIT_NO_TKINTER

    err = capsys.readouterr().err
    assert "tkinter" in err
    assert "apt install python3-tk" in err, "tells the researcher what to do"


def test_os_error_exits_two(monkeypatch, capsys):
    monkeypatch.setattr(
        "iterlab.app.open_interface",
        lambda name: (_ for _ in ()).throw(OSError("unreadable path")),
    )
    assert main(["demo"]) == EXIT_USAGE
    assert "unreadable path" in capsys.readouterr().err


def test_newer_layout_version_exits_one(tmp_path, monkeypatch, capsys):
    from iterlab.cli import EXIT_CANNOT_START

    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo.yaml").write_text("schema_version: 99\nelements: {}\n", encoding="utf-8")
    (tmp_path / "demo.py").write_text("", encoding="utf-8")
    assert main(["demo"]) == EXIT_CANNOT_START
    assert "newer version" in capsys.readouterr().err
