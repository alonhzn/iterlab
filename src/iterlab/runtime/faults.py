"""Reporting faults in the researcher's code without ever ending the session.

There is deliberately **no** fault kind for "no handler written". A control the
researcher has not written code for yet is normal, not a fault, and making the
two representable in one type is exactly how the prior spike conflated them
(spec FR-028, research.md R4/R5).

No GUI imports: the runtime knows only the `FaultSink` protocol, so the whole
fault path is testable with no display.
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from typing import Protocol

LOAD_FAILED = "load_failed"
HANDLER_RAISED = "handler_raised"


@dataclass(frozen=True)
class Fault:
    kind: str
    message: str
    traceback_text: str
    element: str | None = None
    interaction: str | None = None

    def __post_init__(self):
        if self.kind not in (LOAD_FAILED, HANDLER_RAISED):
            raise ValueError(f"unknown fault kind {self.kind!r}")

    @classmethod
    def from_exception(cls, exc, kind, element=None, interaction=None):
        return cls(
            kind=kind,
            message=f"{type(exc).__name__}: {exc}",
            traceback_text="".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
            element=element,
            interaction=interaction,
        )

    def headline(self) -> str:
        if self.element:
            return f"{self.element}: {self.message}"
        return self.message


class FaultSink(Protocol):
    def report(self, fault: Fault) -> None: ...

    def clear(self, element: str | None = None) -> None: ...


class ConsoleFaultSink:
    """Full detail to stderr, leaving stdout to the researcher's own prints."""

    def __init__(self, stream=None):
        self._stream = stream

    @property
    def stream(self):
        return self._stream if self._stream is not None else sys.stderr

    def report(self, fault: Fault) -> None:
        where = f" in {fault.element}" if fault.element else ""
        print(f"\n--- iterlab: error{where} ---", file=self.stream)
        print(fault.traceback_text.rstrip(), file=self.stream)
        print("--- the interface is still running ---\n", file=self.stream)

    def clear(self, element: str | None = None) -> None:
        """Nothing to retract on a console; the scrollback is the record."""


class MultiSink:
    """Fan a fault out to several sinks — stderr and the in-window banner."""

    def __init__(self, *sinks):
        self.sinks = list(sinks)

    def report(self, fault: Fault) -> None:
        for sink in self.sinks:
            sink.report(fault)

    def clear(self, element: str | None = None) -> None:
        for sink in self.sinks:
            sink.clear(element)


class RecordingFaultSink:
    """Test double. Keeps what it was told so tests can assert on it."""

    def __init__(self):
        self.faults = []
        self.cleared = []

    def report(self, fault: Fault) -> None:
        self.faults.append(fault)

    def clear(self, element: str | None = None) -> None:
        self.cleared.append(element)

    @property
    def kinds(self):
        return [f.kind for f in self.faults]
