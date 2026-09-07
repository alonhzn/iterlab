# Implementation Plan: End-to-End Minimal Loop

**Branch**: `001-end-to-end-loop` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-end-to-end-loop/spec.md`

## Summary

Deliver the thinnest complete instance of the iterlab paradigm: a researcher draws a plot area and a
button on a canvas, gets one handler stub per element appended to a paired code file, runs the
interface, and then edits their algorithm repeatedly without ever relaunching or reloading data.

The technical approach is a **strict three-layer split** in which the layout model, code generation,
and the reload/dispatch runtime contain **no GUI imports at all**, and a thin Tk adapter realizes them
on screen. This is driven directly by Principle VII: a release gate that cannot run headlessly is not a
release gate, and the only reliable way to test a GUI tool is to leave almost nothing in the GUI.

Three design consequences fall out of the constitution and dominate everything else:

1. **The session environment is owned by the runtime, never by the researcher's module.** If `ev` were
   defined in the reloaded module, reloading would destroy exactly the data Principle IV promises to
   preserve.
2. **Nothing may hold a reference to a researcher's function object.** Tk and matplotlib callbacks bind
   a dispatcher that resolves the handler by name at the moment of invocation, so a reloaded function
   is picked up with no rebinding step.
3. **Every handler invocation passes through one guarded dispatch path** that distinguishes "no handler
   written" from "handler is broken", because those two are indistinguishable in the prior spike and
   that is the single defect the project most wants not to repeat.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: `tkinter` (standard library, all controls), `matplotlib` (plot rendering only,
embedded via `FigureCanvasTkAgg`), `PyYAML` (layout file format)

**Storage**: Plain files on disk — one `.yaml` layout and one `.py` code file sharing a basename in one
directory. No database, no application state directory, nothing persisted between sessions.

**Testing**: `pytest`. Layout, codegen, and runtime layers test headlessly with no display whatsoever.
The Tk adapter layer tests under a virtual display (`Xvfb` on Linux CI; native display on Windows and
macOS), with `matplotlib` forced to the `Agg` backend where no window is required.

**Target Platform**: Desktop — Windows, macOS, and Linux. Single local user.

**Project Type**: Installable Python package providing a small library API plus two console commands.

**Performance Goals**: Change-detection check adds under 1 ms to an interaction (a single `stat`);
handler dispatch overhead imperceptible; an interface of 20 elements shows no perceptible interaction
delay (SC-007); an edit is in effect on the next interaction within 2 s (SC-003).

**Constraints**: No compiler, no system package step, no post-install configuration. No GUI dependency
outside the standard library. Absence of `tkinter` must produce a named, actionable message rather than
an `ImportError` (constitution, Technology Constraints). Writes to the researcher's `.py` must be atomic.

**Scale/Scope**: One researcher, one machine, one window per interface, on the order of 20–50 elements
per interface, two element types in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Gate | Status |
|---|---|---|---|
| I | Layout Is Drawn, Never Programmed | No public API constructs layout in code; the designer canvas is the only creation path; `edit` and `run` are one command each; opening an unknown name creates it blank | **PASS** |
| II | Layout And Code Are Separate, Name-Linked | `layout/` writes only `.yaml`; `codegen/` writes only `.py`; neither imports the other; paths resolve from the pair's own directory; one schema module is the single source of truth for both designer and runtime | **PASS** |
| III | The Process Never Dies (NON-NEGOTIABLE) | Every invocation passes through one guarded dispatch; `AttributeError` from lookup means "not written" and is silent; anything else is reported through a fault sink and the loop continues | **PASS** |
| IV | Reload Without Loss (NON-NEGOTIABLE) | `ev` is owned by the runtime, defined outside the researcher's module, and outlives every reload; no function object is ever stored; handlers resolve by name at invocation. Recorded as currently requiring a relaunch: a change to startup | **PASS** |
| V | The Researcher's Code Is Additive-Only | `codegen` appends only, never deletes or reorders; existence checked via AST; all writes are write-temp-then-`os.replace`; rename is out of scope this feature so no rewriting path exists at all | **PASS** |
| VI | Tk For Controls, Matplotlib For Plots | Buttons are `tkinter` widgets; plot areas are `FigureCanvasTkAgg` with `NavigationToolbar2Tk`; no `matplotlib.widgets` anywhere; designer and runner share one Tk root and one event path | **PASS** |
| VII | Tested Before Released (NON-NEGOTIABLE) | Three of four layers import no GUI module and test with no display; the Tk layer is thin and smoke-tested under a virtual display; all five Principle III/IV failure modes have named tests | **PASS** |

**Post-Phase-1 re-check**: PASS, unchanged. The design added no dependency and no layer beyond those
listed. See *Complexity Tracking* for the two third-party dependencies and the one accepted limitation.

## Project Structure

### Documentation (this feature)

```text
specs/001-end-to-end-loop/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── layout-schema.md     # The .yaml contract (public surface item 1)
│   ├── handler-api.md       # Naming convention, signature, ev (items 2-4)
│   └── commands.md          # edit / run entry points (item 5)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
src/iterlab/
├── __init__.py           # Public API: edit(name), run(name), __version__
├── cli.py                # Console entry points; tkinter-absence diagnostic
├── errors.py             # Exception types used across layers
├── layout/               # NO GUI IMPORTS
│   ├── schema.py         # Layout, Element; SCHEMA_VERSION; validation; name rules
│   └── store.py          # YAML load/save; atomic write; version gate
├── codegen/              # NO GUI IMPORTS
│   ├── templates.py      # Default stub text per element type; starter file
│   └── inject.py         # AST existence check; additive append; atomic write
├── runtime/              # NO GUI IMPORTS
│   ├── environment.py    # Ev — runtime-owned session state
│   ├── loader.py         # mtime-gated module load/reload; resolve by name
│   ├── dispatch.py       # The single guarded invocation path
│   └── faults.py         # Fault, FaultSink; console sink
└── ui/                   # The ONLY place tkinter/matplotlib are imported
    ├── app.py            # Shared Tk root, menu, lifecycle
    ├── designer.py       # Draw / move / resize / delete / name-on-create
    ├── runner.py         # Realizes a Layout; wires dispatch; deferred first startup
    ├── elements.py       # Element type -> widget factory + event binding
    └── faultbanner.py    # In-window fault signal (FaultSink implementation)

tests/
├── unit/                 # Headless: schema, store, templates, inject, ev
├── integration/          # Headless: loader + dispatch + codegen together
│   ├── test_never_dies.py        # Principle III, all fault classes
│   ├── test_reload.py            # Principle IV, state survival
│   └── test_additive.py          # Principle V, byte-for-byte code file
├── contract/             # Headless: layout schema round-trip, version gate,
│                         #   handler naming, stub shape, command behavior
└── ui/                   # Virtual display: launch, click, resize, toolbar
```

**Structure Decision**: A single installable package under `src/iterlab/`, layered so that `layout`,
`codegen`, and `runtime` are pure logic with no GUI imports, and `ui` is the only module that touches
`tkinter` or `matplotlib`.

This layering is not stylistic. Principle VII forbids releasing without a passing headless suite, and a
GUI-entangled design would push nearly all behavior behind a display requirement. Under this split, the
three constitutional behaviors that are hardest to get right and easiest to regress — never crashing,
reloading without loss, and never damaging researcher code — are all provable with no display at all.
An enforced test asserts that `layout`, `codegen`, and `runtime` import no GUI module, so the boundary
cannot erode silently.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Third-party dependency: `matplotlib` | The only realistic way to give researchers plotting they already know. Named in the constitution's Technology Constraints, so sanctioned rather than novel. | Writing a plotting layer on a Tk canvas would be a project larger than iterlab itself, and researchers would have to learn it. |
| Third-party dependency: `PyYAML` | The constitution fixes YAML as the layout format; Python has no YAML reader in the standard library. | `json` is stdlib but not comfortably hand-editable and carries no comments, failing the constitution's stated reasons for choosing YAML. `tomllib` is read-only in the standard library and awkward for nested element structures. |
| Accepted limitation: module-level code re-runs on reload | Reloading a module necessarily re-executes its top level. A researcher who loads data at module level rather than in startup will see it reload. | Reloading a single function body without its module is fragile and would break closures, decorators, and imports. Mitigated instead by generating a starter file that puts data loading in startup, and by documenting the rule. Recorded in `research.md` as an honest limitation, not a silent one. |
