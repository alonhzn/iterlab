<!--
SYNC IMPACT REPORT
==================
Version change: 2.0.0 → 3.0.0
Bump rationale: MAJOR. Two principles redefined in backward-incompatible ways — I (two commands
becomes one, with an in-interface mode toggle) and VII (a single automation gate becomes two
gates, one of them human). VII is NON-NEGOTIABLE, so Governance requires MAJOR with a recorded
argument regardless.

Modified principles (titles unchanged):
  - I.   Layout Is Drawn, Never Programmed
  - VII. Tested Before Released (still NON-NEGOTIABLE)
  - IV.  Reload Without Loss — one consequential note updated, not redefined

PRINCIPLE I — what changed:
  Removed: "Creating an interface MUST take one command, and running it MUST take one command."
  Added: a single command opens an interface; editing and using it are two modes of one program,
  switched from within the interface; switching MUST NOT require editing Python or running a
  different command. Editor mode MUST provide an element palette and a properties panel, and any
  property settable by dragging MUST also be editable as a value.

  Argument on record: the two-command split forced a researcher who wanted to move a button to
  stop, edit a launcher, and start a different program. That is precisely the ceremony this
  project exists to remove, and it was inherited from the 2024 spike rather than chosen. This
  also reinstates rule R5 from reference/LEARNINGS.md, withdrawn at 1.0.0 because the split was
  thought possibly unsolvable; it is now being solved.

PRINCIPLE VII — what changed:
  Removed: "A test that requires a human to look at a window or click something is not a test."
  Added: two release gates. Gate 1 is the automated headless suite, mandatory for everything
  automatable, and explicitly including all Principle III and IV failure modes. Gate 2 is a
  recorded manual verification pass by the maintainer against a checklist kept in the repository,
  covering only what genuinely cannot be automated, with the list expected to shrink and
  forbidden from growing to absorb work that was merely easier by hand.

  Argument on record: the removed sentence was false for this class of software. Whether a layout
  looks right, an interaction feels immediate, or a fault banner is actually noticeable cannot be
  asserted by a machine. Demanding otherwise would have produced a release process that was either
  dishonest or unusable, and an unusable gate is bypassed rather than met. The requirement that
  Gate 2 be written down and its result recorded is what keeps "verified manually" from decaying
  into "not verified" — and the rule that Gate 2 may hold only non-automatable items keeps it from
  absorbing Gate 1's work.

PRINCIPLE IV — note updated, not redefined:
  The "known today" note said changing startup requires a relaunch. It now observes that the
  Principle I mode toggle supplies that restart without leaving the program, so a startup change
  no longer costs the researcher their whole process.

Consequences for feature 001 (spec, plan, contracts and tasks all require revision):
  - Two commands collapse to one; contracts/commands.md is largely rewritten.
  - A mode toggle, an element palette, and a properties panel are new scope.
  - Renaming an element is back IN scope, because the properties panel makes the name editable.
    This reverses spec FR-005c and reactivates Principle V's sole exception, which 2.0.0's plan
    had recorded as inert for this feature.
  - Toggling to editor mode and back ends the session and starts a fresh one for v1. Applying
    layout edits to a live session without losing state is recorded as the aim, not promised.

---
PRIOR AMENDMENTS
---
2.0.0 (2026-09-07) — MAJOR. Principle IV is NON-NEGOTIABLE, and this narrowed what it guarantees,
which Governance requires be recorded as MAJOR with an explicit argument. Applying that rule the
first time it actually bound is what keeps it from becoming decorative.

Modified principle:
  - IV. Code Changes Take Effect Without Restart → IV. Reload Without Loss (still NON-NEGOTIABLE)

What was removed: the assertion that an edit to researcher code may never require a relaunch, and
the closing line declaring a relaunch acceptable after a visual edit but not after a code edit.

What was retained and strengthened: reload MUST discard nothing; handlers MUST NOT be permanently
bound; `ev` MUST be the first argument. Added as an explicit MUST: `ev` is owned by iterlab and
never defined in the researcher's module, since reloading rebinds module globals.

Argument on record: the removed clause promised something about implementability that had never
been tested — it was written before any code existed. The principle also contradicted itself: the
headline claimed every code edit, while its own first bullet said "only the code of the handler
being invoked is refreshed", which never covered startup. Rather than resolve that by picking the
broader reading and hoping it proves buildable, the scope of what avoids a restart is now treated
as an empirical question answered per feature, with the aim stated and the current limits recorded.
The guarantee that survives is the one the paradigm actually rests on and that is known to be
achievable: a reload never costs the researcher their loaded data.

Consequence for feature 001: editing the startup function requires a relaunch. The in-session
"re-run startup" affordance (spec FR-026c) is withdrawn — re-running setup over a populated
session risks double-opening connections and double-registering callbacks, so a restart is the
correct mechanism rather than a fallback.

1.1.0 (2026-09-07) — MINOR. One principle and one section added; no existing principle removed,
weakened, or redefined. Occasioned by the decision to distribute iterlab as a PyPI package,
which introduces obligations (a release gate and a public-surface compatibility contract)
that did not exist while the project was source-only.

Added in 1.1.0:
  - VII. Tested Before Released (new, NON-NEGOTIABLE)
  - Release And Versioning (new section)
  - Technology Constraints: distribution bullet (PyPI, and the tkinter packaging caveat)
  - Governance: explicit separation of constitution version from package version

Rationale for VII being NON-NEGOTIABLE: a published version cannot be unpublished. PyPI
permits deletion but not reuse of a version number, and any release may already be pinned
by a user. The gate is therefore the only enforcement point that exists.

Key judgment recorded in Release And Versioning: iterlab's public surface is larger than its
Python API. The layout schema, the handler naming convention, the `ev` contract, and the
generated stub shape are all consumed directly by researcher-written code, so breaking any
of them breaks a researcher's existing work rather than merely an integration.

1.0.0 (2026-09-07) — Initial ratification. All template placeholders replaced with concrete,
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

**A single command opens an interface.** Editing the layout and using the interface are two modes
of one program, and the researcher MUST be able to switch between them from within the interface
itself. Switching modes MUST NOT require editing Python, running a different command, or knowing
anything beyond the interface's name. Opening an interface that does not yet exist MUST create a
blank one, together with its starter code file. There is no project scaffolding step, no
registration, and no configuration necessary beyond the interface's name (although some
pre-configurations may be added in the future, like the canvas size or the color template, the
defaults should work well).

Editor mode MUST provide a palette of the element types that can be added, and a properties panel
for the selected element. Properties that can be set by dragging MUST also be editable as values,
so that precise alignment does not depend on a steady hand.

**Rationale**: Hand-coding a layout is the practice this project exists to replace. A tool that
permits it as a convenience will drift toward it, and researchers who have never seen the
alternative will assume it is the intended path. Ceremony at the start of a session is
iteration cost like any other — and being made to stop, edit a launcher, and start a different
program in order to move a button is exactly that ceremony, which is why the two modes belong in
one program.

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

### IV. Reload Without Loss (NON-NEGOTIABLE)

Reloading the researcher's code MUST discard nothing. The environment object and everything in it,
loaded data, computed results, and plots already drawn MUST all survive.

- Handlers MUST NOT be permanently bound at startup. The binding table MUST be refreshable without
  restarting the process. *When* it refreshes — on every invocation, on layout change, on file
  change, or on demand — is an open design choice, not fixed by this principle.
- A single environment object, named `ev`, MUST be the first argument to every handler, and
  elements MUST be reachable from it as attributes under the same name shown in the designer.
- That object MUST be owned by iterlab and MUST NOT be defined in the researcher's module, because
  reloading a module rebinds its globals and would destroy exactly what this principle protects.

**How much can avoid a restart is an empirical question, not a rule.** The aim is that ordinary
changes — altering a function, adding a function, and in time rearranging the layout — take effect
in a live session. How far that reaches depends on what can actually be implemented and made to
work well, so this document deliberately does **not** declare which changes are exempt from a
restart until that has been established in practice. Each feature records what currently requires
a relaunch, and that list is expected to shrink, never to grow.

Known today: changing the startup function requires restarting the session. Re-running setup over
a populated session can double-open connections, double-register callbacks, and double-append
data, and a clean slate is what "startup" means. Note that the mode toggle in Principle I supplies
that restart without leaving the program — switching to editor mode and back ends the session and
begins a fresh one, so a startup change no longer costs the researcher their whole process.

**Rationale**: The paradigm's core economic claim is that expensive data loading happens once per
session rather than once per edit, and that claim rests entirely on reload preserving state. The
prior spike resolved handlers once at startup and cached them, silently making every later code
edit a no-op; that is why late binding is stated here rather than left to the implementation.

An earlier version of this principle also asserted that *no* code edit may ever require a
relaunch. That was written before anything had been built, and it over-committed — it made a
promise about what is implementable without having tested it. What remains is the part that is
both genuinely non-negotiable and known to be achievable: a reload never costs the researcher
what they have already loaded or computed.

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

### VII. Tested Before Released (NON-NEGOTIABLE)

No version of iterlab may be published to PyPI unless **both** release gates pass. There is no
"small fix" exemption, no "docs only" exemption, and no override of either gate.

**Gate 1 — the automated suite.** Everything that can be tested automatically MUST be, and the
suite MUST pass.

- The automated suite MUST run headlessly and unattended, so that it can serve as a gate in
  continuous integration rather than depending on someone's desktop.
- Principles III and IV describe behavior under breakage and MUST be covered automatically, never
  by inspection: a control with no handler, a handler whose module will not parse, a handler that
  raises, a fault present at launch, and a code edit applied mid-session. These are testable
  without a display by design, and that is not an accident — it is why the architecture separates
  the GUI layer from everything else.
- Every defect fixed MUST arrive with a regression test that fails before the fix and passes after.
- Every change to the public surface defined in *Release And Versioning* MUST be accompanied by
  tests showing that artifacts produced by prior versions still work.

**Gate 2 — recorded manual verification.** Some behavior in a graphical tool genuinely cannot be
asserted by a machine: whether a layout looks right, whether an interaction feels immediate,
whether a fault banner is actually noticeable. Before each release the maintainer MUST work
through a written verification checklist and record the result — version, date, outcome, and any
defect found.

- The checklist MUST be written down and kept in the repository. Verification performed from
  memory is not verification.
- A pass that was not recorded did not happen. An unrecorded release is a defect in the process,
  not a technicality.
- The checklist MUST contain **only** what genuinely cannot be automated. Anything on it that
  could be automated is a gap in Gate 1, and belongs there instead.
- The list is expected to shrink as automation improves, and MUST NOT grow to cover work that was
  simply easier to do by hand.

**Rationale**: A published version cannot be withdrawn in any meaningful sense. PyPI allows a
release to be deleted but never allows the version number to be reused, and by then it may
already be pinned in someone's environment. The pre-publish gate is the only point at which
enforcement is still possible, so it is absolute rather than advisory.

An earlier version of this principle demanded that everything be automated, on the reasoning that
a GUI project which defers testing because "it needs a display" ends up with no gate at all. That
reasoning still holds, and Gate 1 carries it: the layering exists precisely so that almost
everything is automatable. But the stronger claim — that a check requiring a human is not a real
check — was false for this kind of software, and pretending otherwise would have produced a
release process that was either dishonest or unusable. Two honest gates are worth more than one
that gets quietly bypassed.

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
- **Distribution**: iterlab is published to PyPI and MUST be installable with a single standard
  install command. It MUST NOT require a compiler, a system package manager step, or any manual
  post-install configuration. The one known caveat MUST be documented rather than papered over:
  `tkinter` ships with CPython on Windows and macOS but is packaged separately on several Linux
  distributions, and no Python dependency declaration can install it. Where it is absent, iterlab
  MUST fail with a message naming the missing component and how to install it, never with an
  unexplained import error.

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
have **automated** coverage asserting that the process survives and that the researcher is
informed. These belong to Gate 1 and MUST NOT be deferred to manual verification.

## Release And Versioning

iterlab is versioned with semantic versioning: **MAJOR.MINOR.PATCH**.

### What iterlab's public surface actually is

Most libraries break their users by changing a function signature. iterlab is not most libraries.
Its public surface includes several things that are consumed directly by code the researcher
wrote, and breaking any of them breaks that researcher's existing work rather than merely an
integration:

1. **The layout file schema** — a layout written by any earlier version MUST open in every later
   version.
2. **The handler naming convention** (`on_<event>_<element_name>`) — this is how every researcher's
   code is wired. Changing it silently unwires every interface ever built.
3. **The handler contract** — that `ev` is the first argument, and that elements are reachable from
   it as attributes under their designer names.
4. **The generated stub shape** — its signature, not its comments.
5. **The commands to edit and to run an interface**, and the file-pairing convention they rely on.
6. **The documented Python API**, if and when one is offered.

A change to any of the six is a breaking change regardless of how small the diff is. A change to
internal structure, private helpers, or the wording of generated comments is not.

### Version rules

- **MAJOR**: any break to the surface above. Reserved for cases where the alternative is worse
  than the migration cost, and never taken for tidiness.
- **MINOR**: new element types, new properties, new capabilities, and any addition that leaves
  every existing interface working untouched.
- **PATCH**: fixes and internal improvements with no surface change.

**While the package is below 1.0.0**, breaking changes MAY occur in a MINOR bump, as semantic
versioning permits. They MUST still be announced in the changelog with migration instructions —
"it's 0.x" is licence to break compatibility, not licence to break it silently. On reaching
1.0.0, items 1 through 5 above become frozen under MAJOR-only.

### Compatibility obligations

- **Layout files are forward-compatible by contract.** A newer iterlab MUST open an older layout.
  Where the schema has moved on, iterlab MUST migrate the file explicitly and tell the researcher
  it did so — never fail, and never silently rewrite.
- **The layout schema carries its own version**, independent of the package version, as required
  by Principle II.
- **Deprecation precedes removal.** Anything on the public surface MUST be deprecated in at least
  one MINOR release, with a warning naming the replacement, before removal in a MAJOR release.
- **Every release MUST have a changelog entry** stating what changed and, for any breaking change,
  what a researcher must do about it.

**Rationale**: The people this tool serves are not software engineers maintaining a dependency
graph; they are researchers who will return to an analysis after six months and expect it to run.
An interface built today must still open in two years. That expectation is the whole basis for
trusting a tool with an algorithm, and it is far easier to honor from the first release than to
retrofit after the first careless break.

## Governance

This constitution supersedes all other development practices in this project. Where a
convention, a habit, or an external tutorial conflicts with it, this document wins.

**Amendment procedure**: Amendments MUST be proposed as an edit to this file with a written
rationale, MUST state the version bump and its justification, and MUST update the Sync Impact
Report at the head of the file. Principles III, IV, and VII are marked NON-NEGOTIABLE: they may
be clarified or strengthened, but weakening or removing any of them requires an explicit MAJOR
bump and a recorded argument for why the project survives without it.

**Two version numbers exist and MUST NOT be conflated:**

| Number | Governs | Where it lives |
|---|---|---|
| **Constitution version** | This document's governance | The Version line below |
| **Package version** | The released software, under the rules in *Release And Versioning* | Package metadata and the changelog |

They move independently. Amending this document does not release anything, and releasing does not
amend this document.

**Versioning policy for this document** — semantic versioning of governance:

- **MAJOR**: a principle is removed or redefined in a backward-incompatible way.
- **MINOR**: a principle or section is added, or existing guidance is materially expanded.
- **PATCH**: clarifications, wording, and non-semantic refinements.

**Compliance review**: Every plan documents its Constitution Check. Every review verifies that
changed code upholds Principles III, IV, and V in particular, since these govern behavior that
is easy to regress and invisible until a researcher loses work or time. Complexity that is not
justified MUST be removed rather than documented.

**Release review**: Every release additionally verifies, before publishing, that the automated
suite passes and the manual verification checklist has been worked through and recorded (both
gates of Principle VII), that the version bump matches the rules in *Release And Versioning*, that
the changelog entry exists, and that any breaking change carries migration instructions. A release
that cannot satisfy all of these is not made.

**Runtime guidance**: agent-specific development guidance lives alongside the project (e.g.
`CLAUDE.md`) and MUST remain consistent with this constitution. Where the two disagree, this
document governs and the guidance file is corrected.

**Version**: 3.0.0 | **Ratified**: 2026-09-07 | **Last Amended**: 2026-09-07
