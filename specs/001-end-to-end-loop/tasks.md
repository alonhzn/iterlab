# Tasks: End-to-End Minimal Loop

**Input**: Design documents from `/specs/001-end-to-end-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: **Required.** Constitution Principle VII (NON-NEGOTIABLE) defines two release gates —
Gate 1 the automated suite, Gate 2 a recorded manual checklist. Test tasks are first-class throughout,
and `VERIFICATION.md` is a deliverable, not an afterthought.

**Organization**: Grouped by user story so each can be implemented and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on incomplete work
- **[Story]**: Which user story the task serves (US1–US4)
- Every task names its exact file path

## Path Conventions

Single project. Source at `src/iterlab/`, tests at `tests/`, per plan.md.

**Two rules govern every task:**

1. `layout/`, `codegen/`, and `runtime/` MUST NOT import `tkinter`, `matplotlib`, or any GUI module.
   Only `ui/` may. T019 enforces this automatically.
2. `codegen/rename.py` is the **only** module permitted to modify a line the researcher wrote.
   Everything else is strictly additive.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: A package that installs, a suite that runs, and both release gates in place.

- [X] T001 Create `pyproject.toml` at repository root: package metadata, `requires-python = ">=3.10"`, runtime dependencies `matplotlib` and `pyyaml`, a `dev` extra with `pytest`, a **single** console entry point `iterlab = "iterlab.cli:main"`, and src-layout packaging pointing at `src/`
- [X] T002 Create the package skeleton with `__init__.py` in each of `src/iterlab/`, `src/iterlab/layout/`, `src/iterlab/codegen/`, `src/iterlab/runtime/`, `src/iterlab/ui/`
- [X] T003 [P] Create the test tree: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/ui/`
- [X] T004 [P] Create `tests/conftest.py`: force `matplotlib` to the `Agg` backend before any import, and provide a `tmp_interface` fixture yielding a temporary directory with a `.yaml`/`.py` pair
- [X] T005 [P] Declare pytest settings in `pyproject.toml`: marker `ui` (requires a display), with `tests/ui` excluded from the default run
- [X] T006 [P] Create `.github/workflows/ci.yml` running the headless suite on Windows, macOS, and Linux, plus `tests/ui` under `xvfb-run` on Linux — this is Gate 1
- [X] T007 [P] Create `VERIFICATION.md` at repository root with the Gate 2 structure: a checklist section, a recorded-results table (version, date, outcome, defects found), and a stated rule that it holds only what cannot be automated and is expected to shrink

**Checkpoint**: `pip install -e ".[dev]"` succeeds, `pytest` runs green on an empty suite, both gates exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Primitives every user story needs. No story-specific behavior lives here.

**⚠️ No user story can start until this phase completes.**

- [X] T008 Create `src/iterlab/errors.py` defining `IterlabError`, `LayoutInvalid`, `LayoutVersionTooNew`, `NameInvalid`, `NameInUse`, and `CodeFileUnparseable`
- [X] T009 [P] Implement `src/iterlab/layout/schema.py`: `SCHEMA_VERSION = 1`, `Rect`, `Element`, `Window`, `Layout` per data-model.md, plus `validate_name()` enforcing `isidentifier()`, not a keyword, no leading underscore, and uniqueness (FR-005b, R10)
- [X] T010 [P] Write `tests/unit/test_schema.py`: valid and invalid names including keywords, leading underscore and non-identifiers; rect bounds rejection when `left + width > 1`; duplicate-name rejection
- [X] T011 Implement `src/iterlab/layout/store.py`: `load()` and `save()` for contracts/layout-schema.md, atomic write via temp-file-then-`os.replace`, element order preservation, 4-decimal rounding, and the version gate that reports and refuses a file whose `schema_version` exceeds `SCHEMA_VERSION` without opening or writing it back (FR-036a, FR-036b)
- [X] T012 [P] Write `tests/contract/test_layout_schema.py`: `test_roundtrip_byte_identical`, `test_newer_version_refused` (asserting the file is neither opened nor modified on disk), unknown-key rejection, and a minimal empty-elements layout
- [X] T013 [P] Implement `src/iterlab/runtime/environment.py`: the `Ev` class, constructed by the runtime, holding element handles as named attributes and reserving the `_` prefix for iterlab's own state (FR-018, FR-019, R1)
- [X] T014 [P] Write `tests/unit/test_environment.py`: researcher attributes persist, element handles are reachable by name, underscore-prefixed names are reserved
- [X] T015 [P] Implement `src/iterlab/runtime/faults.py`: the `Fault` value with `kind` limited to `load_failed` and `handler_raised`, the `FaultSink` protocol, `ConsoleFaultSink` writing tracebacks to stderr, and a `MultiSink` — note there is deliberately **no** fault kind for "no handler written" (FR-028, R5)
- [X] T016 [P] Write `tests/unit/test_faults.py`: console sink formatting, multi-sink fan-out, and a `RecordingFaultSink` test double for reuse by later phases
- [X] T017 Implement `src/iterlab/ui/app.py`: the single Tk root that lives for the whole process, ownership of the current `Mode`, a `build(mode)` / `teardown()` pair that destroys every content widget and builds the other mode's, and the guarded `tkinter` import raising a named, actionable error (R12, R13)
- [X] T018 Implement `src/iterlab/cli.py`: `main()` taking one positional name, name resolution per contracts/commands.md (bare name, path, or `.yaml`/`.py` form, anchored to the pair's own directory), and exit codes 0/1/2/3
- [X] T019 [P] Write `tests/unit/test_import_boundary.py`: assert that importing `iterlab.layout`, `iterlab.codegen`, and `iterlab.runtime` pulls in no module whose name starts with `tkinter` or `matplotlib` — the guard that keeps Gate 1 headless

**Checkpoint**: Layout files round-trip, faults report, names validate, `iterlab --help` works, layering guard passes.

---

## Phase 3: User Story 1 - Draw an interface and use it, in one program (Priority: P1) 🎯 MVP

**Goal**: One command opens an interface. The researcher picks a type from the palette, drags it out,
names it in the properties panel, toggles to GUI mode, and clicking the button runs their code.

**Independent test**: Give someone only the tool's name. They must produce a window with a working
button and then move it — without ever leaving the program (SC-001, SC-010).

### Tests for User Story 1

- [X] T020 [P] [US1] Write `tests/unit/test_templates.py`: the generated stub signature matches contracts/handler-api.md, exactly one stub per element, and the starter file steers data loading into `on_startup`
- [X] T021 [P] [US1] Write `tests/integration/test_create_and_run.py`: opening a name that does not exist creates both files; creating an element appends exactly one stub; the default stub is `on_clicked_<name>` for both element types and no hover/motion/key stubs appear (FR-017d)
- [X] T022 [P] [US1] Write `tests/unit/test_start_mode.py`: an interface with no elements resolves to editor mode, one with elements resolves to GUI mode (FR-001a)
- [X] T023 [P] [US1] Write `tests/ui/test_mode_toggle.py` marked `ui`: the toggle is present in both modes, switching rebuilds the window contents, the Tk root and window geometry persist, and `ev` is discarded on leaving GUI mode (FR-015, FR-015a, FR-015d, R13)
- [X] T024 [P] [US1] Write `tests/ui/test_window_launch.py` marked `ui`: GUI mode places both elements proportionally, `Button.invoke()` fires the handler, and `on_startup` ran before any interaction

### Implementation for User Story 1

- [X] T025 [P] [US1] Implement `src/iterlab/codegen/templates.py`: the default stub text per element type and the starter code file body, exactly as specified in contracts/handler-api.md
- [X] T026 [US1] Implement `src/iterlab/codegen/inject.py`: parse with `ast`, collect top-level function names, append a stub only when absent, write atomically via temp-file-then-`os.replace` (FR-009, FR-013, R6)
- [X] T027 [US1] Implement `src/iterlab/runtime/loader.py` first pass: load the researcher's module by path and resolve a handler by name, returning a distinct "not defined" outcome for `AttributeError` from the lookup (R4)
- [X] T028 [US1] Implement `src/iterlab/runtime/dispatch.py` first pass: the single guarded invocation path that resolves the handler at call time, invokes it with `(ev, event)`, and never stores a function object (R2)
- [X] T029 [P] [US1] Implement the normalized `Event` in `src/iterlab/runtime/dispatch.py` per data-model.md, carrying `kind`, `element`, `button`, `x`, `y`, `key`, `double`
- [X] T030 [US1] Implement `src/iterlab/ui/elements.py`: a `tkinter.Button` for `button`, a `FigureCanvasTkAgg` with `NavigationToolbar2Tk` for `plot_area`; Tk events for controls and `mpl_connect` for plots; both normalized into `Event` with **data coordinates** for plots (FR-017e, R9, Principle VI)
- [X] T031 [US1] Implement geometry in `src/iterlab/ui/elements.py` using `place()` with `relx`/`rely`/`relwidth`/`relheight` from normalized positions, with fonts in fixed points so text does not scale (FR-021a, FR-021b, R8)
- [X] T032 [P] [US1] Implement `src/iterlab/ui/modetoggle.py`: the top-left toggle, rendered above all elements, present in both modes, never obscured, and not part of the layout (FR-015a, FR-015b, FR-015c)
- [X] T033 [P] [US1] Implement `src/iterlab/ui/palette.py`: the element-type palette listing every addable type, so the vocabulary is discoverable without documentation (FR-003a)
- [X] T034 [US1] Implement `src/iterlab/ui/properties.py` first pass: display the selected element's properties, show a clear empty state when nothing is selected, and accept a name at creation with the next available default pre-filled (FR-005a, FR-006a)
- [X] T035 [US1] Implement `src/iterlab/ui/designer.py` creation flow: choose a type from the palette, drag out a rectangle, confirm the name, and place the element on the canvas (FR-003)
- [X] T036 [US1] Wire designer creation in `src/iterlab/ui/designer.py` to `layout/store.save()` and `codegen/inject.append()` so an element persists and its stub appears with no explicit save action (FR-008)
- [X] T037 [US1] Implement `src/iterlab/ui/runner.py`: realize a `Layout` into the content frame, populate `ev` with element handles, invoke `on_startup` once, and wire every element to `dispatch`
- [X] T038 [US1] Implement mode switching in `src/iterlab/ui/app.py`: teardown discards all content widgets and the `ev`; build creates the other mode, and entering GUI mode creates a fresh `ev` and runs startup (FR-015d, FR-015e, R13)
- [X] T039 [US1] Implement `run(name)` in `src/iterlab/__init__.py` and connect it in `src/iterlab/cli.py`, creating a missing pair before opening and choosing the start mode by whether elements exist (FR-001, FR-001a, FR-002)

**Checkpoint**: The two-minute path in quickstart.md works end to end. **This is the MVP.**

---

## Phase 4: User Story 2 - Change the algorithm without restarting (Priority: P2)

**Goal**: Edit a handler, click again, new code runs — loaded data and drawn plots untouched.

**Independent test**: Load data slowly in `on_startup`, edit only the click handler, re-trigger. The
handler updates and the slow load does not repeat (SC-003, SC-008).

### Tests for User Story 2

- [X] T040 [P] [US2] Write `tests/integration/test_reload.py::test_env_survives_reload`: `ev` and its contents are the same objects across a reload
- [X] T041 [P] [US2] Write `tests/integration/test_reload.py::test_unchanged_file_not_reloaded`: repeated invocations with no edit do not re-execute the module (FR-026a)
- [X] T042 [P] [US2] Write `tests/integration/test_reload.py::test_startup_not_rerun`: editing `on_startup` does not re-invoke it and leaves session state intact (FR-026b, FR-026e)
- [X] T043 [P] [US2] Write `tests/integration/test_reload.py::test_failed_startup_retried`: startup that never completed runs once the code is fixed, without a restart (FR-026d)
- [X] T044 [P] [US2] Write `tests/integration/test_reload.py::test_new_handler_becomes_live`: a handler added after launch works without restarting (FR-025)

### Implementation for User Story 2

- [X] T045 [US2] Extend `src/iterlab/runtime/loader.py` with change detection: record `(st_mtime_ns, st_size)` on successful load, compare before each resolution, `importlib.reload` only when the stamp differs (FR-026, FR-026a, R2)
- [X] T046 [US2] Implement the `LoadedModule` state machine in `src/iterlab/runtime/loader.py` per data-model.md — `UNLOADED`, `CURRENT`, `STALE`, `BROKEN` — with `BROKEN` explicitly non-terminal so every later interaction retries the load (FR-031)
- [X] T047 [US2] Implement startup lifecycle in `src/iterlab/ui/runner.py`: track whether startup completed successfully, never re-invoke it once it has, and attempt it on the next interaction if it never completed (FR-026b, FR-026d, FR-026e)
- [X] T048 [US2] Confirm `src/iterlab/ui/runner.py` offers no in-session re-run of startup, and that nothing clears plot areas on reload (FR-026c, FR-024)

**Checkpoint**: Quickstart steps 1–4b pass. The paradigm's central claim is demonstrable.

---

## Phase 5: User Story 3 - Keep working when the code is broken (Priority: P3)

**Goal**: A typo never ends the session. The researcher is told what broke, fixes it, and continues —
while an element with no handler stays silently inert.

**Independent test**: Introduce a syntax error, an import failure, and a raising handler in turn. Each
time the session survives and reports; recovery needs only a fix (SC-004, SC-009).

### Tests for User Story 3

- [X] T049 [P] [US3] Write `tests/integration/test_never_dies.py`: unparseable file, failing import, raising handler, and a fault present at launch — each reports a `Fault`, none ends the session (FR-027, FR-030, FR-032)
- [X] T050 [P] [US3] Write `tests/integration/test_never_dies.py::test_missing_handler_is_silent`: a missing handler produces **no** fault — the case that must never be conflated with broken code (FR-028, FR-029)
- [X] T051 [P] [US3] Write `tests/integration/test_never_dies.py::test_recovery_preserves_state`: after a fault is fixed, the handler runs and prior session data is intact (FR-031)
- [X] T052 [P] [US3] Write `tests/ui/test_fault_banner.py` marked `ui`: the banner names the failed element, other elements stay usable while it shows, and it clears once corrected code runs (FR-033a, FR-033b)

### Implementation for User Story 3

- [X] T053 [US3] Implement three-stage fault classification in `src/iterlab/runtime/dispatch.py`: module-load failure is `load_failed`; `AttributeError` from the name lookup is "not written" and silent; anything raised by the handler is `handler_raised` (R4)
- [X] T054 [US3] Emit a "cleared" signal from `src/iterlab/runtime/dispatch.py` when a previously failing element invokes successfully, so sinks can retract a stale report (FR-033b)
- [X] T055 [US3] Implement `src/iterlab/ui/faultbanner.py` as a `FaultSink`: a non-blocking in-window banner naming the element and the failure, never requiring dismissal, clearing on the cleared signal (FR-033, FR-033a, FR-033b)
- [X] T056 [US3] Attach both console and banner sinks in `src/iterlab/ui/runner.py`, and open the window even when the code file fails to load at launch (FR-032, FR-033)

**Checkpoint**: Quickstart steps 5 and 6 pass, and case 6 is visibly distinguishable from case 5.

---

## Phase 6: User Story 4 - Refine elements without disturbing the code (Priority: P4)

**Goal**: Move, resize, retype coordinates, relabel, rename, and delete — with the researcher's code
file byte-for-byte untouched apart from appended stubs and renamed handlers.

**Independent test**: Take an interface with substantial hand-written code, make several layout and
property changes including a rename, and diff. Only added stubs and renamed handlers may appear
(SC-006, SC-012).

**⚠️ This phase contains the only code path permitted to modify existing lines. Build `rename.py`
against its tests before wiring it to the UI.**

### Tests for User Story 4

- [X] T057 [P] [US4] Write `tests/integration/test_additive.py::test_code_file_byte_identical`: moving and resizing elements leaves the `.py` byte-for-byte unchanged (FR-014)
- [X] T058 [P] [US4] Write `tests/integration/test_additive.py::test_no_duplicate_after_reformat`: a reformatted file with decorators and comments is still detected, and no duplicate stub is appended (FR-011)
- [X] T059 [P] [US4] Write `tests/integration/test_additive.py::test_delete_leaves_handler`: deleting an element removes it from the layout and leaves its handler in place (FR-012)
- [X] T060 [P] [US4] Write `tests/integration/test_additive.py::test_unparseable_file_refuses_append`: when the code file will not parse, the append is refused and reported (R6)
- [X] T061 [P] [US4] Write `tests/unit/test_atomic_write.py`: an interrupted write leaves the original file intact and never truncated (FR-013)
- [X] T062 [P] [US4] Write `tests/integration/test_rename.py::test_only_handler_names_change`: after a rename, comments, string literals, local variables, formatting and ordering are byte-identical — only the handler identifiers differ (FR-005d, R14)
- [X] T063 [P] [US4] Write `tests/integration/test_rename.py::test_all_handlers_for_element_renamed`: every interaction's handler for that element is renamed together (FR-005d)
- [X] T064 [P] [US4] Write `tests/integration/test_rename.py::test_other_elements_untouched`: a handler for a *different* element whose name contains the old name as a substring is not renamed — the case a text substitution would get wrong (R14)
- [X] T065 [P] [US4] Write `tests/integration/test_rename.py::test_refused_on_unparseable`: a rename on a file that will not parse is refused and reported, leaving both files unmodified (FR-005f)
- [X] T066 [P] [US4] Write `tests/integration/test_rename.py::test_invalid_or_taken_name_rejected`: a keyword, a non-identifier, and an in-use name are each rejected with nothing changed (FR-005e)
- [X] T067 [P] [US4] Write `tests/ui/test_properties_panel.py` marked `ui`: typing coordinates moves the element, dragging to the same values produces an identical layout file, editing a label changes only the label, and an invalid value is rejected leaving the element unchanged (FR-006c, FR-006d, FR-006e)

### Implementation for User Story 4

- [X] T068 [US4] Implement `src/iterlab/codegen/rename.py`: locate top-level `FunctionDef` nodes named `on_<interaction>_<old_name>` for every known interaction, rewrite **only those identifiers** by AST node position rather than text substitution, copy everything else through byte for byte, write atomically, and refuse outright if the file does not parse (FR-005d, FR-005f, R14)
- [X] T069 [US4] Implement selection, move, and resize in `src/iterlab/ui/designer.py`, persisting position changes through `layout/store.save()` with no write to the code file whatsoever
- [X] T070 [US4] Implement deletion in `src/iterlab/ui/designer.py`: remove the element from the layout, leave its handler untouched in the code file (FR-012)
- [X] T071 [US4] Extend `src/iterlab/ui/properties.py` to edit position numerically and a button's label, keeping canvas and panel in sync in both directions, and rejecting invalid values with an explanation (FR-006b, FR-006c, FR-006d, FR-006e)
- [X] T072 [US4] Wire renaming in `src/iterlab/ui/properties.py`: validate the new name, call `codegen/rename.py` **first**, and only on success update the layout — so a failure leaves the two files consistent (FR-005c, FR-005e, R14)
- [X] T073 [US4] Harden `src/iterlab/codegen/inject.py`: refuse to append when the file does not parse, reporting why, and confirm AST detection tolerates decorators, comments, and reformatting (FR-011, R6)
- [X] T074 [US4] Restore existing elements onto the canvas at their saved positions when editor mode is entered, in `src/iterlab/ui/designer.py` (FR-007)

**Checkpoint**: Quickstart steps 7 through 7d pass with a clean diff.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T075 [P] Implement the `tkinter`-missing diagnostic end to end in `src/iterlab/cli.py`, exiting `3` with the component name and install command, covered in `tests/unit/test_cli.py` by simulating the absent import (R12)
- [X] T076 [P] Write `tests/unit/test_cli.py` for name resolution: bare name, relative path, absolute path, `.yaml` and `.py` forms, and anchoring to the pair's directory rather than the working directory (FR-035)
- [X] T077 [P] Write `tests/ui/test_resize.py` marked `ui`: elements keep proportions at several window sizes while text size stays constant (FR-021a, FR-021b)
- [X] T078 [P] Write `tests/ui/test_toolbar.py` marked `ui`: pan and zoom work on a plot area with no handler written for it (FR-017e)
- [X] T079 [P] Write `tests/ui/test_perf.py` marked `ui`: a 20-element interface stays responsive, and mode switching completes within budget (SC-007, SC-010 — the S1b regression from the prior spike)
- [X] T080 [P] Populate the Gate 2 checklist in `VERIFICATION.md` with only what cannot be automated: whether the layout looks right, whether the toggle feels instant, whether the fault banner is genuinely noticeable, whether the palette reads as discoverable. Each item states what to look at and what "pass" means
- [X] T081 [P] Write `README.md` usage section and `CHANGELOG.md` with an `0.1.0` entry, both required before any release by the constitution's Release Review
- [X] T082 Run every scenario in `specs/001-end-to-end-loop/quickstart.md` by hand and record the outcome, including confirmation that the module-level-reload limitation from research.md R3 is documented in the generated starter file
- [X] T083 Verify both release gates: Gate 1 passes headlessly with no display present and `tests/ui` passes under a virtual display; Gate 2's checklist is complete and its result recorded in `VERIFICATION.md`

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundational   ← blocks everything
    ↓
Phase 3 US1 (P1) ──────────────── MVP, and the base the rest extend
    ↓
Phase 4 US2 (P2)   extends loader + runner
    ↓
Phase 5 US3 (P3)   extends dispatch + runner
    ↓
Phase 6 US4 (P4)   extends designer + properties + inject; adds rename
    ↓
Phase 7 Polish
```

### User Story Dependencies

This is a walking skeleton, so later stories deepen the components US1 creates rather than adding
separate ones. Being honest about that beats pretending to four independent slices:

- **US1** depends only on Phase 2. Delivers a complete, demonstrable product.
- **US2** extends US1's `loader.py` and `runner.py`. Independently *testable*, not independently
  *buildable*.
- **US3** extends US1's `dispatch.py`. Independently testable.
- **US4** extends US1's `designer.py`, `properties.py` and `inject.py`, and adds `rename.py`.
  Independently testable.

US2, US3, and US4 do not depend on **each other** and may be built in any order once US1 lands.

### Within Each User Story

Tests first — every one maps to a named requirement, so they are cheap to state. Then models, then
services, then UI wiring. In Phase 6 this ordering is not optional: `rename.py` must satisfy T062–T066
before T072 wires it to anything a researcher can click.

### Parallel Opportunities

- Phase 1: T003–T007 all parallel.
- Phase 2: T009, T013, T015, T019 are independent files, each with its test following. T011 depends on
  T009; T017 and T018 depend on T008.
- Phase 3: test tasks T020–T024 all parallel. T025, T029, T032, T033 are independent implementation
  files.
- Phase 4: test tasks T040–T044 parallel. Implementation T045–T048 is sequential — two files.
- Phase 5: test tasks T049–T052 parallel.
- Phase 6: test tasks T057–T067 all parallel — eleven of them, the largest parallel block in the plan.
- Phase 7: T075–T081 all parallel.

---

## Parallel Example: User Story 4

```text
# The eleven test tasks together — different files or different test functions:
T057-T061  tests/integration/test_additive.py, tests/unit/test_atomic_write.py
T062-T066  tests/integration/test_rename.py
T067       tests/ui/test_properties_panel.py

# Then rename in isolation, before any UI touches it:
T068       src/iterlab/codegen/rename.py

# Then the UI work, which can proceed in parallel once T068 is green:
T069-T070  src/iterlab/ui/designer.py
T071-T072  src/iterlab/ui/properties.py
T073       src/iterlab/codegen/inject.py
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

Phases 1–3, tasks T001–T039. A researcher opens one command, draws an interface, toggles to GUI mode
and uses it — already a complete product, and the first moment the paradigm is visible to someone who
has never seen it.

### Incremental Delivery

1. **US1** → a GUI you never programmed, in one program with a mode toggle. Demonstrable.
2. **US2** → the iteration loop. This is the release that makes the case for the paradigm; before it,
   iterlab is a pleasant GUI builder.
3. **US3** → survivable in real use. US2 without US3 is fragile in practice, since the first typo
   forces the restart US2 exists to eliminate.
4. **US4** → survivable past the first hour, once there is code worth protecting.

Do not ship publicly before US3. US2 alone demos beautifully and disappoints immediately.

### Parallel Team Strategy

After Phase 2, one person takes US1 to its checkpoint since everything builds on it. Once US1 lands,
US2, US3, and US4 can proceed simultaneously — they touch `loader.py`/`runner.py`, `dispatch.py`, and
`designer.py`/`properties.py`/`rename.py` respectively, with only `runner.py` shared between US2 and
US3.

---

## Notes

- **The layering rule is not stylistic.** T019 fails the build if `layout`, `codegen`, or `runtime`
  ever import a GUI module. Everything in Phases 4–6 that proves a constitutional guarantee runs with
  no display because of it.
- **T064 is the test that catches the obvious wrong implementation of rename.** A text substitution of
  the old name passes T062 and T063 and fails T064, because it also rewrites handlers belonging to
  other elements whose names contain the old one. Write it before `rename.py`.
- **T050 is the single most important test in the suite.** It asserts that a missing handler produces
  no fault, which is the defect that stopped the prior spike. It is easy to regress later by
  "improving" error reporting.
- **T080 defines Gate 2's scope.** Anything on that checklist that could have been automated is a gap
  in Gate 1, not a manual step. Keep it short and keep it honest.
- **Commit after each checkpoint.** Each is a working, demonstrable increment.
