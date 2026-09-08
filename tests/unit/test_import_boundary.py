"""The layering rule, enforced.

`layout`, `codegen`, and `runtime` must import no GUI module. This is what makes
the headless tier of Gate 1 possible at all, and it is easy to break by adding
one convenient import — so it is asserted rather than trusted.
"""

import subprocess
import sys

PURE = ["iterlab.layout.schema", "iterlab.layout.store", "iterlab.codegen.templates",
        "iterlab.runtime.environment", "iterlab.runtime.faults"]

PROBE = """
import sys
for mod in {modules!r}:
    __import__(mod)
banned = sorted(
    m for m in sys.modules
    if m.split(".")[0] in ("tkinter", "matplotlib", "_tkinter")
)
print(",".join(banned))
"""


def test_pure_layers_import_no_gui_module():
    """Run in a fresh interpreter: this test's own imports must not pollute it."""
    result = subprocess.run(
        [sys.executable, "-c", PROBE.format(modules=PURE)],
        capture_output=True,
        text=True,
        check=True,
    )
    leaked = [m for m in result.stdout.strip().split(",") if m]
    assert not leaked, (
        f"GUI modules reached a pure layer: {leaked}. "
        f"layout/, codegen/ and runtime/ must import no GUI module — that is "
        f"what keeps the headless release gate possible."
    )
