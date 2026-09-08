"""The fault channel, with no display anywhere in sight."""

import io

import pytest

from iterlab.runtime.faults import (
    HANDLER_RAISED,
    LOAD_FAILED,
    ConsoleFaultSink,
    Fault,
    MultiSink,
    RecordingFaultSink,
)


def _fault(kind=HANDLER_RAISED, element="run_fit"):
    try:
        raise ValueError("boom")
    except ValueError as exc:
        return Fault.from_exception(exc, kind=kind, element=element, interaction="clicked")


def test_only_two_fault_kinds_exist():
    """There is deliberately no kind for 'no handler written'.

    Conflating that with broken code is the defect that stopped the prior spike,
    so it is made unrepresentable rather than merely discouraged.
    """
    with pytest.raises(ValueError):
        Fault(kind="no_handler", message="x", traceback_text="")


def test_from_exception_captures_type_message_and_traceback():
    fault = _fault()
    assert "ValueError" in fault.message and "boom" in fault.message
    assert "ValueError" in fault.traceback_text
    assert fault.element == "run_fit"


def test_console_sink_writes_to_its_stream_and_says_it_survived():
    stream = io.StringIO()
    ConsoleFaultSink(stream).report(_fault())
    text = stream.getvalue()
    assert "ValueError" in text
    assert "still running" in text


def test_console_sink_names_the_element():
    stream = io.StringIO()
    ConsoleFaultSink(stream).report(_fault(element="run_fit"))
    assert "run_fit" in stream.getvalue()


def test_load_failure_has_no_element_attributed():
    fault = _fault(kind=LOAD_FAILED, element=None)
    assert fault.element is None
    assert fault.headline() == fault.message


def test_multisink_fans_out_reports_and_clears():
    a, b = RecordingFaultSink(), RecordingFaultSink()
    multi = MultiSink(a, b)
    multi.report(_fault())
    multi.clear("run_fit")
    assert a.kinds == b.kinds == [HANDLER_RAISED]
    assert a.cleared == b.cleared == ["run_fit"]
