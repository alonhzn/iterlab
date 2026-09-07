# Quickstart & Validation: End-to-End Minimal Loop

**Feature**: 001-end-to-end-loop | **Date**: 2026-09-07

How to run the feature and how to prove it works. Contract details live in
[contracts/](./contracts/); entity definitions in [data-model.md](./data-model.md).

---

## Prerequisites

- Python 3.10+
- On Linux only: `tkinter` is a separate distribution package — `apt install python3-tk` or
  `dnf install python3-tkinter`. It ships with CPython on Windows and macOS. Running without it should
  exit `3` with a message naming it, never an `ImportError` (R12).
- For the display-dependent tests on Linux CI: `Xvfb`.

```console
pip install -e ".[dev]"
```

---

## The two-minute path (SC-001)

This is the scenario a first-time researcher must complete in under two minutes, having written no
layout code.

```console
iterlab demo
```

One command. Creates `demo.yaml` and `demo.py`, and — because the interface has no elements yet —
opens in **editor mode**: a blank canvas with a palette and a properties panel beside it.

Pick "plot area" from the palette and drag out a wide rectangle. The properties panel shows its
properties with `plot_0` already filled in; rename it to `spectrum`. Pick "button", drag a smaller
rectangle, name it `run_fit`, and set its label to "Run fit".

`demo.py` now ends with one stub per element — click handlers only, nothing for hover or motion
(FR-017d). Edit it:

```python
import numpy as np

def on_startup(ev):
    ev.x = np.linspace(0, 10, 500)      # loaded once per session
    ev.spectrum.plot(ev.x, np.sin(ev.x))

def on_clicked_run_fit(ev, event):
    ev.spectrum.clear()
    ev.spectrum.plot(ev.x, np.sin(2 * ev.x))
```

Click the toggle in the **top-left corner**. The window becomes GUI mode and shows the sine curve.
Clicking **Run fit** redraws it at double frequency. Click the toggle again and you are back on the
canvas — no command, no file edit, no restart.

From now on, `iterlab demo` opens straight into GUI mode, because the interface has elements
(FR-001a).

---

## Proving the paradigm (the part that matters)

**Leave the window open for everything below.** If you ever have to restart it, the feature has failed.

### 1. A code change takes effect with no restart (US2, FR-022)

Edit `on_clicked_run_fit` to use `3 * ev.x`. Save. Click **Run fit**.

Expect: the new frequency. No restart, no reload of `ev.x`.

### 2. Loaded data survives (FR-023, SC-005)

Add a slow load to `on_startup`, restart once so it runs, then edit only the click handler and click
again.

Expect: the handler updates; the slow load does **not** repeat. This is the feature's entire economic
claim, so time it.

### 3. Repeated clicks cost nothing (FR-026a)

Click **Run fit** ten times without editing anything.

Expect: no reloading between clicks. A `print()` at module level should appear at most once.

### 4. Editing startup does not re-run it (FR-026b, FR-026c)

Change the startup code. Click **Run fit**.

Expect: the click handler is current, startup did **not** re-run, `ev.x` is untouched. There is no
affordance to re-run startup *within* a live session, and none should be offered. To apply a startup
change, start a fresh session — toggling to the editor and back is enough (FR-015e). This is
deliberate: re-running setup over a populated session risks double-opening connections and
double-registering callbacks, whereas a fresh session has nothing to double.

### 4b. A startup that never ran does get another chance (FR-026d)

Put a syntax error in `on_startup`, then launch. The window opens and reports the fault (FR-032), but
startup never completed. Now fix the error and click **Run fit**.

Expect: startup runs for the first time, `ev.x` appears, and the session becomes usable — **without
relaunching**. This is a deferred first run, not a re-run: nothing had been initialized, so nothing can
be double-initialized. Without it, a typo in startup would strand the researcher, which Principle III
forbids.

### 5. A typo does not kill the session (US3, FR-027, FR-030)

Introduce a syntax error. Save. Click **Run fit**.

Expect: window stays open; a full traceback on stderr; a non-blocking banner naming `run_fit`. Fix the
typo, click again — it works, the banner clears (FR-033b), and `ev.x` was never lost. Under 10 seconds
end to end (SC-009).

### 6. An unwritten handler is silent (FR-029)

Draw a second button, do not write anything for it, click it.

Expect: nothing happens, and **nothing is reported**. This must look different from case 5 — that
distinction is the defect this project exists not to repeat.

### 7. Layout edits do not touch your code (US4, SC-006)

`cp demo.py demo.py.bak`, then toggle to the editor, move and resize things, add a third button, and
toggle back.

```console
diff demo.py.bak demo.py
```

Expect: added lines only. Zero modifications to existing lines.

### 7b. Numeric geometry (FR-006c, SC-011)

Select the plot area and type exact values into its position fields.

Expect: it moves to precisely those coordinates. Dragging it to the same values must produce an
identical layout file — the two input routes are one operation.

### 7c. Rename rewrites handlers and nothing else (FR-005d, SC-012)

`cp demo.py demo.py.bak`. Select `run_fit`, rename it to `fit_button`, then diff.

Expect: `on_clicked_run_fit` became `on_clicked_fit_button`, and **every other line is identical** —
comments, strings, formatting, ordering. Then check the negative cases: a name that is a Python
keyword, a name already in use, and a rename attempted while `demo.py` has a syntax error. Each must be
refused with an explanation, leaving both files untouched.

### 7d. A mode switch ends the session (FR-015d)

With data loaded and a plot drawn, toggle to the editor and back.

Expect: startup runs again and the data is reloaded. This is the feature's known limit, not a bug —
live layout editing with state preserved is the aim, and is deliberately not promised yet.

### 8. Resize behaves (FR-021a, FR-021b)

Drag the window much larger.

Expect: elements keep proportions; button labels and axis text stay the same readable size.

### 9. Plot toolbar works unaided (FR-017e)

Pan and zoom the plot with no handler written for it.

---

## Running the tests — Gate 1

```console
pytest tests/unit tests/integration tests/contract    # no display needed
pytest tests/ui                                       # needs a display
xvfb-run -a pytest tests/                             # everything, Linux CI
```

The first command is the important one: it covers every Principle III, IV, and V behavior with no
display at all, because `layout`, `codegen`, and `runtime` import no GUI module. A display problem in
CI therefore blocks only `tests/ui`.

**Gate 1 is the full automated suite** (Principle VII). No publish on a red suite, no exemptions.

## Manual verification — Gate 2

Some things cannot be asserted by a machine: whether the layout *looks* right, whether the toggle feels
instant, whether the fault banner is genuinely noticeable rather than merely present. Those live in
`VERIFICATION.md`, and the maintainer works through them and records the result — version, date,
outcome — before each release. A pass that was not recorded did not happen.

The list holds **only** what cannot be automated. Anything on it that could be automated is a gap in
Gate 1 and belongs there instead. It is expected to shrink.

### Tests that map to constitutional guarantees

| Test | Asserts |
|---|---|
| `integration/test_never_dies.py` | Session survives: unparseable file, failing import, raising handler, fault at launch. Each reports; none exits |
| `integration/test_never_dies.py::test_missing_handler_is_silent` | A missing handler produces **no** fault — the case that must not be conflated |
| `integration/test_reload.py::test_env_survives_reload` | `ev` and its contents identical across a reload |
| `integration/test_reload.py::test_startup_not_rerun` | Editing startup does not re-invoke it |
| `integration/test_reload.py::test_failed_startup_retried` | A startup that never completed runs once the code is fixed |
| `integration/test_reload.py::test_unchanged_file_not_reloaded` | Module not re-executed when the stamp is unchanged |
| `integration/test_additive.py::test_code_file_byte_identical` | Layout edits leave the `.py` byte-for-byte unchanged |
| `integration/test_additive.py::test_no_duplicate_after_reformat` | Reformatted file still detected; no duplicate stub |
| `contract/test_layout_schema.py::test_roundtrip_byte_identical` | Load/save with no edits changes nothing |
| `contract/test_layout_schema.py::test_newer_version_refused` | Newer file is not opened **and not written back** |
| `integration/test_rename.py::test_only_handler_names_change` | A rename leaves comments, strings, locals and formatting byte-identical |
| `integration/test_rename.py::test_other_elements_untouched` | Handlers merely containing the old name as a substring are not renamed |
| `integration/test_rename.py::test_refused_on_unparseable` | A rename on an unparseable file is refused, and the file is unmodified |
| `unit/test_import_boundary.py` | `layout`, `codegen`, `runtime` import no GUI module — the layering that makes the gate possible |

---

## Known limitation to verify is documented, not fixed

Reloading a module re-executes its top level, so a researcher who writes `data = load()` at module
level rather than in `on_startup` will see it reload on the first interaction after any edit
(research.md R3). This cannot be prevented. Confirm that the generated starter file steers data
loading into `on_startup` and says why.
