<!--
SYNC IMPACT REPORT
==================
Version change: (unratified template) → 1.0.0
Bump rationale: Initial ratification. All template placeholders replaced with concrete,
project-specific governance derived from reference/LEARNINGS.md sections 4 and 5.

Principles defined (6; template scaffold offered 5 slots, extended by one):
  - I.   Layout Is Drawn, Never Programmed          (new)
  - II.  Layout And Code Are Separate, Name-Linked  (new)
  - III. The Process Never Dies                      (new, NON-NEGOTIABLE)
  - IV.  Code Changes Take Effect Without Restart    (new, NON-NEGOTIABLE)
  - V.   The Researcher's Code Is Additive-Only      (new)
  - VI.  Tk For Controls, Matplotlib For Plots       (new)

Sections added:
  - Technology Constraints (SECTION_2)
  - Development Workflow (SECTION_3)
  - Governance

Sections removed: none (initial ratification)

Provenance: every principle traces to a rule (R1-R7) or decision (K1-K11) in
reference/LEARNINGS.md, which in turn traces to a documented failure (S1-S12) of the
2024 rrGUI spike. Rule R5 was withdrawn during author review and is deliberately absent;
the edit/run mode split is an open design question, not a governed constraint.

Dependent artifacts: .specify/templates/{plan,spec,tasks,checklist}-template.md read this
constitution at runtime and require no modification. No pending updates.

Deferred TODOs: none. RATIFICATION_DATE set to the date of first adoption (2026-09-07).
-->

# iterlab Constitution

iterlab exists to bring an unnamed but decades-proven paradigm to Python: the GUI as the
**development environment for an algorithm**, not as a wrapper placed over a finished program.
The researcher draws a small interactive surface — plots, buttons, fields, selectors — and
develops the algorithm inside it, offloading the overhead of re-running, re-loading, re-opening
figures, and re-typing parameters onto the interface.

Every principle below is subordinate to one measure: **the length of the researcher's iteration
loop**. Where a rule and that measure appear to conflict, the conflict is a design defect to be
resolved, not a trade-off to be silently taken.

## Core Principles

### I. Layout Is Drawn, Never Programmed

Visual layout MUST be created and modified by direct manipulation — drag, drop, and resize of
visual elements on a canvas. iterlab MUST NOT require, or offer as the primary path, the
construction of layout in Python code.

Creating an interface MUST take one command, and running it MUST take one command. Opening an
interface that does not yet exist MUST create a blank one, together with its starter code file.
There is no project scaffolding step, no registration, and no configuration beyond the
interface's name.

**Rationale**: Hand-coding a layout is the practice this project exists to replace. A tool that
permits it as a convenience will drift toward it, and researchers who have never seen the
alternative will assume it is the intended path. Ceremony at the start of a session is
iteration cost like any other.

### II. Layout And Code Are Separate, Name-Linked Files

An interface is a `.yaml` layout file and a `.py` code file sharing a basename in one folder.
The **only** coupling between them is the *name* of an element. Adding, moving, resizing, or
restyling an element MUST NOT alter the code file, and editing the code file MUST NOT alter the
layout file.

- The layout file MUST resolve relative to the folder holding the pair, never relative to the
  process's current working directory.
- The designer and the runtime MUST share one layout schema. Every property the runtime reads
  MUST be writable in the designer, and every property the designer writes MUST be understood by
  the runtime.
- That schema MUST be versioned and extensible per element type, with defaults such that a
  minimal element stays terse.

**Rationale**: This separation is what lets a researcher rearrange an interface at any point in
the life of the code without fear. The schema requirement is not housekeeping: in the prior
spike the designer and runtime drifted apart at three widget types, to the point where an
element created in the designer crashed the runtime.

### III. The Process Never Dies (NON-NEGOTIABLE)

The Python process MUST NOT terminate because of a fault in the researcher's code. Fixing that
code MUST NEVER require restarting the process.

Two distinct situations MUST be distinguished and MUST NOT be conflated:

| Situation | Required response |
|---|---|
| A control has no handler defined | Continue. This is normal and expected — a control may be drawn long before its behavior is written. |
| A handler's module fails to import or raises — syntax error, bad import, exception at any point | Continue, **and report the failure visibly to the researcher with its traceback**. |

Never crash, always tell. A control that silently does nothing when its code is broken is a
defect of the same severity as a crash.

**Rationale**: Tearing down and relaunching the process is precisely the cost this project
exists to eliminate; a crash on a typo forfeits the tool's entire value proposition. But the
converse error is equally damaging: the prior spike caught every exception with a bare `except:`
and made "not written yet" indistinguishable from "your file has a syntax error," leaving the
researcher clicking a dead control with no message anywhere.

### IV. Code Changes Take Effect Without Restart (NON-NEGOTIABLE)

An edit to the researcher's code MUST take effect without closing and relaunching the interface.

- **Reload MUST discard nothing.** The environment object and everything in it, loaded data,
  computed results, and plots already drawn MUST all survive. Only the code of the handler being
  invoked is refreshed.
- Handlers MUST NOT be permanently bound at startup. The binding table MUST be refreshable
  without restarting the process. *When* it refreshes — on every invocation, on layout change, on
  file change, or on demand — is an open design choice, not fixed by this principle.
- A single environment object, named `ev`, MUST be the first argument to every handler, and
  elements MUST be reachable from it as attributes under the same name shown in the designer.

Requiring a relaunch after a *visual* edit is an accepted trade-off, since layout changes are far
rarer than code changes. Requiring one after a *code* edit is not.

**Rationale**: This is the paradigm's core economic claim — expensive data loading happens once
per session rather than once per edit. The prior spike resolved handlers once at startup and
cached them, which silently made every later code edit a no-op; the constraint is stated here
because it must shape the binding design from the first line, not be retrofitted.

### V. The Researcher's Code Is Additive-Only

Generated edits to the researcher's `.py` file MUST be additive. No deletion, no rewriting, and
no reordering of code the researcher wrote.

- Creating an element appends a handler stub. An element already known to the file MUST be
  skipped, so re-editing a layout never duplicates or clobbers.
- **Sole exception**: renaming an element MUST also rename its handlers in the code file, and
  MUST change nothing else. Leaving a researcher to hand-repair broken name links would defeat
  the purpose of the tool.
- Deleting an element MUST NOT delete its handler. Orphaned handlers are acceptable; destroyed
  work is not.
- All writes to the researcher's file MUST be atomic — write to a temporary file, then replace.
  In-place rewriting of an open handle is prohibited.

**Rationale**: The researcher's code is the actual work product; the tool is scaffolding around
it. Any tool that can lose that work will not be trusted with it, and trust here is binary. The
atomicity requirement is specific: the prior spike rewrote files through an open read-write
handle, where an interruption corrupts the file.

### VI. Tk For Controls, Matplotlib For Plots

Every interactive control MUST be a Tk widget. matplotlib MUST be used only to render plots,
inside embedded canvases. No control may be implemented as a `matplotlib.widgets` widget,
whatever the short-term convenience.

The designer and the runtime MUST share one window model and one event path.

**Rationale**: This is the correction of the prior spike's root architectural mistake, which
failed in two ways at once. matplotlib has no dropdown, no list box, and no real label, so the
widget vocabulary was capped below what the paradigm requires; and matplotlib is inefficient at
hosting many widgets in one figure, so interfaces grew slower precisely as they became useful.
Both failures resolve under this single division of labor.

## Technology Constraints

**Minimal dependencies, minimal complexity.** This is a deliberate constraint, not an aspiration.

- **GUI toolkit**: Tk (`tkinter`), from the standard library. Chosen over PySide/PyQt, Dear
  PyGui, and wxPython specifically because it ships with Python.
- **Plotting**: matplotlib, embedded — and confined to the role defined in Principle VI.
- **Layout format**: YAML. Human-readable, diffable in version control, and hand-editable when
  the designer cannot yet express something. A binary or pickled format would fail all three and
  MUST NOT be adopted.
- **Element positions**: normalized [0, 1] fractions of the window, so that layouts are
  resolution-independent and window resize is not a special case.
- **Handler binding**: by naming convention (`on_<event>_<element_name>`), requiring no
  registration boilerplate from the researcher.
- Any additional runtime dependency MUST be justified against the minimal-dependency constraint
  and recorded in the plan's Complexity Tracking section. "It would be convenient" is not a
  justification.

## Development Workflow

**Legacy reference material is read-only.** Everything under `reference/` is historical. The
2024 spike at `reference/legacy-rrGUI/` MUST NOT be imported, executed, modified, or placed on
the import path. `reference/LEARNINGS.md` is the only file in that tree the Spec Kit workflow
reads. Porting any code out of `legacy-rrGUI/` requires an explicit task in `tasks.md` naming
the source file and lines.

**Specification precedes implementation.** Features proceed through `/speckit-specify` →
`/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Implementation
detail MUST NOT be introduced into a specification; a spec describes what a researcher can do
and why.

**Every plan MUST pass a Constitution Check** before task generation, and again after design.
Violations are either corrected or recorded in Complexity Tracking with an explicit rationale
for why the simpler alternative was rejected.

**Failure modes are tested, not assumed.** Principles III and IV describe behavior under
breakage, which cannot be verified by inspection. A control with no handler, a handler whose
module has a syntax error, a handler that raises, and a code edit applied mid-session MUST each
have automated coverage asserting that the process survives and that the researcher is informed.

## Governance

This constitution supersedes all other development practices in this project. Where a
convention, a habit, or an external tutorial conflicts with it, this document wins.

**Amendment procedure**: Amendments MUST be proposed as an edit to this file with a written
rationale, MUST state the version bump and its justification, and MUST update the Sync Impact
Report at the head of the file. Principles III and IV are marked NON-NEGOTIABLE: they may be
clarified or strengthened, but weakening or removing either requires an explicit MAJOR bump and
a recorded argument for why the paradigm survives without it.

**Versioning policy** — semantic versioning of governance:

- **MAJOR**: a principle is removed or redefined in a backward-incompatible way.
- **MINOR**: a principle or section is added, or existing guidance is materially expanded.
- **PATCH**: clarifications, wording, and non-semantic refinements.

**Compliance review**: Every plan documents its Constitution Check. Every review verifies that
changed code upholds Principles III, IV, and V in particular, since these govern behavior that
is easy to regress and invisible until a researcher loses work or time. Complexity that is not
justified MUST be removed rather than documented.

**Runtime guidance**: agent-specific development guidance lives alongside the project (e.g.
`CLAUDE.md`) and MUST remain consistent with this constitution. Where the two disagree, this
document governs and the guidance file is corrected.

**Version**: 1.0.0 | **Ratified**: 2026-09-07 | **Last Amended**: 2026-09-07
