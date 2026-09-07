# Phase 0 Research: End-to-End Minimal Loop

**Feature**: 001-end-to-end-loop | **Date**: 2026-09-07

Each finding below resolved an unknown in the plan's Technical Context. Findings R1, R2, and R7 are
the ones that shape the architecture; the rest constrain individual components.

---

## R1. Keeping session state alive across a reload

**Decision**: The session environment `ev` is constructed and owned by `runtime/environment.py` and
passed *into* handlers as their first argument. It is never defined in, imported from, or stored in the
researcher's module. Reloading the researcher's module has no effect on it whatsoever.

**Rationale**: `importlib.reload()` re-executes a module's top level and rebinds its globals. Anything
the researcher's module owns is therefore destroyed and rebuilt on every reload. Since Principle IV
requires that loaded data, computed results, and drawn plots all survive, the only safe place for that
state is *outside* the reloaded unit. Making `ev` a parameter rather than an import also removes any
temptation to reach for module globals, which is the pattern the paradigm replaces.

This also explains a detail of the prior spike that initially looked arbitrary: it created its
environment object in the runtime and passed it to every callback. That was correct, and it is kept.

**Alternatives considered**:
- *Environment as a module-level singleton in the researcher's file* — destroyed by every reload. Fails
  Principle IV outright.
- *Snapshot and restore state around each reload* — requires deep-copying arbitrary research objects
  (open file handles, live figures, hardware sessions). Unreliable and expensive.
- *Store state in a module the researcher imports but never edits* — works, but adds an import the
  researcher must remember and can accidentally reload.

---

## R2. Picking up code changes without rebinding callbacks

**Decision**: No component ever stores a reference to a researcher's function object. Tk and matplotlib
callbacks are bound once, at window construction, to a **dispatcher closure** that captures only the
element name and interaction kind. At invocation the dispatcher asks `runtime/loader.py` for the
current function by name, and the loader reloads the module first if the file's modification time has
changed since it was last loaded.

**Rationale**: This is the direct correction of the defect that stopped the prior spike, where handlers
were resolved once at startup and cached in a dictionary, silently making every later edit a no-op. If
nothing holds a function object, there is nothing to invalidate and no rebinding step that can be
forgotten. It also satisfies FR-026 (checked at each interaction) and FR-026a (not reapplied when
unchanged) with the same mechanism: the `stat` is the check, and the reload is skipped when the
timestamp is unchanged.

Measured cost is a single `os.stat` per interaction — microseconds, and far below the 1 ms budget.

**Alternatives considered**:
- *A background file watcher* — considered and rejected during clarification. Adds a thread, and a
  reload can land in the middle of an interaction.
- *Re-resolve on layout change only* — permitted by Principle IV's wording, but layout changes require
  a relaunch in this feature, so it would never fire.
- *Explicit reload control* — rejected during clarification: one manual step per iteration is exactly
  the friction the tool removes.

**Caveat carried forward**: modification-time granularity is coarse on some filesystems (1 s on older
FAT/HFS+). A save followed within the same tick by an interaction could be missed. Mitigation: compare
`(st_mtime_ns, st_size)` together, which catches essentially all real edits.

---

## R3. Reload re-executes module top level — an accepted, documented limitation

**Decision**: Accept that `importlib.reload()` re-runs everything at the module's top level. Steer
researchers away from the hazard by generating a starter file whose comments direct data loading into
the startup function, and document the rule plainly in the quickstart.

**Rationale**: A researcher who writes `data = load_everything()` at module level rather than inside
startup will see that line re-execute on the first interaction after any edit — the exact slow reload
Principle IV exists to prevent. There is no way to reload a module without re-running its top level.
The honest response is to make the safe path the obvious one and state the limitation rather than
letting researchers discover it as mysterious slowness.

Note the interaction with FR-026b: *startup is never re-run implicitly* refers to iterlab calling the
researcher's startup function. Module top-level statements are a different thing and are outside
iterlab's control.

**Alternatives considered**:
- *Recompile only the changed function and patch it in* — brittle against closures, decorators, and
  imports; a well-known source of subtle bugs in hot-reload systems.
- *Execute the module in a fresh namespace and diff* — same top-level re-execution, more machinery.
- *Forbid module-level statements* — hostile to researchers, and unenforceable.

---

## R4. Distinguishing "no handler written" from "handler is broken"

**Decision**: Two failure points, handled separately, in `runtime/dispatch.py`:

| Stage | Failure | Meaning | Response |
|---|---|---|---|
| Load the module | Any exception (`SyntaxError`, `ImportError`, anything raised at top level) | The code is broken | Report through the fault sink; interaction is a no-op; session continues |
| Look up the name | `AttributeError` only | No handler written | Silent no-op; entirely normal |
| Call the handler | Any exception | The handler is broken | Report with traceback; session continues |

Nothing anywhere catches a bare exception without classifying it first.

**Rationale**: The prior spike wrapped all three stages in one bare `except:` and produced an identical
silent no-op for every case, so a syntax error looked exactly like an unwritten handler. Separating the
stages is what makes FR-028 testable rather than aspirational. Restricting the "not written" branch to
`AttributeError` specifically is the key detail: it is the only exception `getattr` raises for a missing
name, so nothing else can be misclassified as absence.

**Alternatives considered**:
- *Pre-scan the module's AST for the handler name* — works, but says nothing about whether the module
  loads, and duplicates work the import already does.
- *Require handler registration by decorator* — would eliminate the ambiguity, but breaks the zero-
  boilerplate convention and would mean researchers cannot simply delete a stub.

---

## R5. Reporting a fault to two channels without coupling to the GUI

**Decision**: `runtime/faults.py` defines a `Fault` value (element name, interaction, kind, message,
formatted traceback) and a `FaultSink` protocol with one method. The runtime knows only the protocol.
Two implementations exist: a console sink that writes full detail to standard error, and a Tk banner
sink in `ui/faultbanner.py`. Both are attached at once, satisfying FR-033's two channels. A successful
invocation of a previously failing handler emits a "cleared" signal, which the banner consumes and the
console ignores (FR-033b).

**Rationale**: This keeps the entire fault path testable with no display — tests attach a recording
sink and assert on `Fault` values directly. It also means the two-channel requirement is a composition
detail rather than something threaded through the dispatch logic.

**Alternatives considered**:
- *Dispatch writes directly to `stderr` and calls into the UI* — puts a GUI import in the runtime layer
  and makes fault behavior untestable headlessly.
- *Python `logging`* — a reasonable transport, but researchers do not configure logging, and a fault
  here is a first-class user-facing event rather than a diagnostic record.

---

## R6. Where handler stubs are inserted, and how existence is detected

**Decision**: Detect existing handlers by parsing the file with `ast` and collecting top-level
`FunctionDef` names. Append new stubs at **end of file**, after a blank-line separator. Write by
building the full new text, writing it to a temporary file in the same directory, and calling
`os.replace()`.

**Rationale**: AST parsing is immune to reformatting, comments, and decorators in a way that regex
matching is not — this is the one technique from the prior spike worth porting nearly intact.
Appending at end of file, rather than the spike's approach of inserting after the startup function,
means the insertion point never depends on the researcher's file structure and cannot land inside a
class body or a conditional block.

`os.replace()` is atomic on both POSIX and Windows, which is what FR-013 requires. The temporary file
must be in the same directory so the replace is not a cross-device move.

One consequence: if the researcher's file does not currently parse, existence detection cannot run.
In that case the correct behavior is to refuse to append and report why, rather than appending blindly
and risking a duplicate definition.

**Alternatives considered**:
- *Regex search for `def on_clicked_x`* — breaks on decorators, unusual whitespace, and commented-out
  code that mentions the name.
- *Insert after the startup function, as the spike did* — depends on the startup function still
  existing and being at top level; the spike had to add a repair path for when it was deleted.
- *Write through an open read-write handle* — the spike's approach; an interruption truncates the
  researcher's file. Explicitly prohibited by Principle V.

---

## R7. Testing a GUI tool headlessly

**Decision**: Two tiers.

**Tier 1 — no display at all.** The `layout`, `codegen`, and `runtime` packages import no GUI module,
so the whole of schema validation, file round-tripping, stub generation, AST injection, atomic writes,
module reloading, handler resolution, fault classification, and fault reporting is testable as ordinary
Python. This covers every Principle III, IV, and V behavior. An automated test asserts the import
boundary itself, so the layering cannot decay unnoticed.

**Tier 2 — virtual display.** A small suite covers what genuinely requires a window: launching,
clicking a real button, resizing, and the plot toolbar. On Linux CI this runs under `Xvfb`; on Windows
and macOS a display is present natively. Where a window is not needed, `matplotlib` is forced to the
`Agg` backend.

**Rationale**: Principle VII requires a headless, unattended suite as the release gate, and a GUI
project that treats testing as a display problem ends up with no gate at all. Inverting the question —
*how little can live behind the display?* — is what makes the gate achievable. Tier 2 exists because
some things genuinely cannot be faked, but it stays small enough that a display problem in CI blocks
only a thin slice rather than the whole suite.

Tk specifics that make Tier 2 workable: a `Tk` root can be created against a virtual display;
`Button.invoke()` triggers a callback without synthesising a mouse event; `update()` and
`update_idletasks()` pump the event loop deterministically so a test never sleeps.

**Alternatives considered**:
- *Mock `tkinter` wholesale* — tests would pass against a fiction, proving nothing about real widget
  behavior.
- *Put everything behind a display and require Xvfb for the whole suite* — makes the release gate
  hostage to CI display setup, and slows the loop that developers actually run.
- *Manual verification checklist* — explicitly disallowed by Principle VII.

---

## R8. Proportional geometry with fixed text

**Decision**: Position and size elements with Tk's `place()` geometry manager using the relative
options (`relx`, `rely`, `relwidth`, `relheight`), fed directly by the normalized `[0, 1]` values
already stored in the layout. Fonts are set explicitly in points and are never scaled.

**Rationale**: This makes FR-021a nearly free: `place()` with relative options recomputes geometry on
every window resize, which is exactly proportional scaling, with no resize handler to write. Because Tk
font sizes are independent of widget geometry, FR-021b is satisfied by simply not touching them. The
normalized storage the constitution already mandates maps one-to-one onto the geometry manager's own
model.

**Alternatives considered**:
- *`grid` or `pack`* — both compute layout from widget content and weights, which cannot express
  free-form drawn positions.
- *A manual `<Configure>` handler recomputing pixel geometry* — reimplements what `place()` already
  does, with more code and more chances to be wrong.

---

## R9. Events: Tk for controls, matplotlib for plots

**Decision**: Controls bind Tk events (`<Button-1/2/3>`, `<Enter>`, `<Leave>`, `<Motion>`, `<Key>`).
Plot areas bind matplotlib canvas events via `mpl_connect`. Both normalize into one iterlab event
object before reaching the researcher, so a handler signature does not depend on which element type
raised it.

**Rationale**: A researcher clicking inside a plot needs **data coordinates**, not pixels — that is the
entire point of clicking a plot in a research tool, and only matplotlib can supply them. Tk events
carry no notion of data space. Using each system where it is authoritative is therefore not a
compromise but the correct division, and it matches Principle VI's split of responsibilities.

Normalizing both into one event type keeps FR-017a's promise that the interaction set is universal
rather than per-type, and keeps the handler contract stable if an element type later changes its
underlying widget.

**Alternatives considered**:
- *Tk events everywhere, converting pixels to data coordinates by hand* — duplicates matplotlib's
  transform logic and breaks the moment axes are rescaled.
- *Pass the native event through untouched* — leaks the widget toolkit into the handler signature,
  making it public surface that cannot change without a MAJOR release.

---

## R10. Element names must be valid in Python

**Decision**: A name is accepted only if `name.isidentifier()` is true, `keyword.iskeyword(name)` is
false, it does not begin with an underscore, and it is not already used in the interface. Rejection
happens at the moment of entry in the designer, with a message naming the reason.

**Rationale**: The name becomes part of a function name (`on_clicked_<name>`) and an attribute on `ev`,
so an invalid one produces either a syntax error in generated code or an unreachable element. FR-005b
requires catching this at entry rather than at failure. The leading-underscore rule keeps the `ev`
namespace clear for internal attributes.

**Alternatives considered**:
- *Silently sanitize the name* — the researcher's code would then refer to a name they never chose.
- *Validate only at generation time* — the failure surfaces far from the cause, which is precisely what
  FR-005b prohibits.

---

## R11. Schema version gate

**Decision**: Every layout file carries an integer `schema_version`, written as `1` by this release.
On load: a version equal to the current one proceeds; a *lower* version has no migration path in this
release and cannot occur, since this is the first; a *higher* version is reported and the file is not
opened, not partially interpreted, and above all not written back.

**Rationale**: FR-036a/b. The refusal to open a newer file is the important half — reading a newer
layout, silently dropping properties this build does not understand, and saving it back would destroy
the researcher's work in a way that is invisible until they open it on the newer version again. That is
precisely the class of data loss Principle V exists to prevent. Migration machinery is deliberately
deferred (FR-036c) until there is a real schema change to migrate.

**Alternatives considered**:
- *Best-effort open of unknown versions* — silent data loss on the next save.
- *No version field until needed* — the one field that cannot be added retroactively to files already
  written.

---

## R12. Missing `tkinter` must be diagnosable

**Decision**: `cli.py` attempts to import `tkinter` inside a guarded block before doing anything else,
and on failure exits with a message that names the missing component and gives the install command for
common Linux distributions.

**Rationale**: The constitution's Technology Constraints require exactly this. `tkinter` ships with
CPython on Windows and macOS but is a separate distribution package on Debian, Ubuntu, Fedora and
others, and no Python dependency declaration can install it. Without this guard, the first experience
of a Linux researcher installing iterlab is a bare `ModuleNotFoundError: No module named 'tkinter'`,
which does not tell them what to do.

**Alternatives considered**:
- *Declare it as a dependency* — impossible; it is not on PyPI in any usable form.
- *Let the import error surface* — technically informative, practically useless to the target audience.
