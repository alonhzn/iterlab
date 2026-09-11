"""The release gate reads the results table, not the whole document.

Gate 2 is the recorded manual pass, and the constitution is blunt about it: "A
pass that was not recorded did not happen." The check that asks whether it
happened first asked whether the version string appeared anywhere in
VERIFICATION.md - and 1.4.0 passed on the strength of a checklist item reading
"open a project made before 1.4.0". The one automated question standing between
an unverified build and an upload that cannot be withdrawn was answered by
prose about something else.

No GUI, no network: this is the gate's own arithmetic.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from preflight import recorded_gate_two  # noqa: E402

TABLE = """\
## Checklist

| 53 | Open a project made before 1.4.0 | copies appear | the commonest crossing |

## Recorded results

| Version | Date | Platform | Outcome | Defects found |
|---|---|---|---|---|
| 1.3.1 | 2026-09-09 | Windows 11 | Pass | 0 |
"""


def test_a_row_in_the_table_counts():
    assert recorded_gate_two(TABLE, "1.3.1") is True


def test_the_version_named_in_the_checklist_does_not():
    """The defect, exactly: mentioned above the table, not recorded in it."""
    assert "1.4.0" in TABLE
    assert recorded_gate_two(TABLE, "1.4.0") is False


def test_a_version_nobody_mentioned_does_not():
    assert recorded_gate_two(TABLE, "9.9.9") is False


def test_a_near_miss_is_not_a_match():
    """`1.3.1` must not be satisfied by a row for `1.3.10` or `v1.3.1`."""
    table = TABLE.replace("| 1.3.1 |", "| 1.3.10 |")
    assert recorded_gate_two(table, "1.3.1") is False


def test_a_document_with_no_table_at_all():
    assert recorded_gate_two("# nothing here\n", "1.4.0") is False


@pytest.mark.parametrize("version", ["1.3.1"])
def test_the_real_document_is_read_the_same_way(version):
    """Guards against the table heading being renamed out from under this."""
    text = (Path(__file__).resolve().parents[2] / "VERIFICATION.md").read_text(
        encoding="utf-8"
    )
    assert "## Recorded results" in text, "the check keys off this heading"
    recorded_gate_two(text, version)  # must not raise on the real file
