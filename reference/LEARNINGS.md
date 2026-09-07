# Learnings from `legacy-rrGUI`

**Source**: `C:\Users\alonh\rrGUI`, copied to `reference/legacy-rrGUI/`
**Age**: 2 commits, both 2024-03-24. A spike, abandoned — not a project that decayed.
**Size**: 830 lines across 4 source files.
**Prior names**: `EZplt` → `rrGUI` → (now) `iterlab`.
**Reviewed and corrected by the author**: 2026-09-07.

> This document is the ONLY thing the Spec Kit workflow reads about the old project.
> The code under `legacy-rrGUI/` is read-only and is never imported, executed, or modified.

---

## 1. Intent

*(Stated without reference to any implementation.)*

Most GUIs are built **after** a program works, to wrap a functioning command-line tool in something
friendly. That is one legitimate use of a GUI, but the widespread belief that it is the *only* correct
use has hidden a second, fundamentally different paradigm.

In engineering and research, the GUI can be the **development environment for the algorithm itself**.
Instead of writing a script, running it, waiting, reading numbers, closing figures, editing constants,
and running again, the researcher builds a small interactive surface — plots, buttons, input fields,
selectors — and iterates *inside* it. The overhead of re-running, re-loading data, re-opening figures,
and re-typing parameters is offloaded onto the interface. What remains is the algorithm.

This is the paradigm behind MathWorks GUIDE and App Designer, and it is close to unknown in Python.
Researchers either rediscover it alone or, far more commonly, never learn it exists. Some write GUI
layouts by hand in code, which defeats the entire point.

The product exists to bring this paradigm to Python. Its non-negotiable commitments:

1. **Layout is never programmed.** It is drawn — direct manipulation of visual elements
   (plot areas, buttons, radio buttons, text fields, labels, lists, dropdowns) by drag, drop, and resize.
2. **Layout and algorithm live in separate files.** Moving, resizing, or adding a visual element cannot
   disturb the research code. The only link between them is the *name* of an element. Creating an
   element adds a handler to the code file — an additive operation, never a destructive one.
3. **Changes to the algorithm take effect immediately**, without closing and relaunching the interface,
   and **without losing anything already in memory** — loaded data, computed results, and plots already
   drawn all survive. Only the code inside the handler being invoked is refreshed. Layout changes are
   rarer than code changes, so requiring a relaunch after a *visual* edit is an accepted trade-off;
   requiring one after a *code* edit is not.
4. **The tool never crashes on the researcher's account.** A half-finished interface, a control with no
   code behind it yet, a syntax error mid-edit — none of these may take down the process, because
   taking down the process is exactly the cost the paradigm exists to eliminate.

The measure of success is the length of the researcher's iteration loop, not the polish of the output.

---

## 2. What worked

Behaviors the spike got right. These should survive into the new product.

| # | Behavior | Where |
|---|---|---|
| W1 | Layout stored in a separate human-readable file; the code file has no layout in it at all | `example1.yaml` vs `example1.py` |
| W2 | Creating an element **appends** a handler stub to the code file; an element already known to the file is skipped, so re-editing layout never duplicates or clobbers | `gui_maker.py:202-224` |
| W3 | A single environment object is passed as the first argument to every handler — the researcher's place to keep data and state across interactions without globals. The name `ev` is good: short for environment, which hosts all the objects, and because the user will type it many, many times, a two-letter name earns its keep | `user_gui_aux.py:9-22` |
| W4 | Elements are reachable from code as named attributes on that object, using the same name shown in the designer | `user_gui_aux.py:18-22, 26, 41, 61` |
| W5 | **A control with no code behind it is a no-op, not a crash.** The researcher can draw the whole interface first and fill in behavior later, or delete a stub they do not want | `user_gui_aux.py:35-36` — see S3 for the one flaw in how this is implemented |
| W6 | Positions stored as fractions of the window, so a layout is resolution-independent and rescales | `example1.yaml`, `gui_maker.py:425-440` |
| W7 | The designer is a direct-manipulation canvas: drag out a rectangle to create, click an existing element to reselect and resize | `gui_maker.py:75-109, 189-199` |
| W8 | Generated stubs are commented in a friendly, permission-giving voice ("Yes, you are allowed to delete it if it is of no use to you") | `function_templates.py:17-37` |
| W9 | **One command to edit an interface, one command to run it** — `edit_gui('name')` / `run_gui('name')`, nothing else to configure. Editing a name that does not exist silently creates a blank interface with a starter `.py` alongside it. There is no "new project" ceremony | `example1.py:57-59`, `gui_maker.py:468-491` |

---

## 3. Where it stalled

The honest post-mortem. Weight this section heavily — it is the reason the spike stopped.

### S1. matplotlib was used as the GUI toolkit — the root architectural mistake

Every control in the spike is a `matplotlib.widgets` widget. That single decision produced two separate
failures, and together they are why the project stopped.

**S1a — the widget vocabulary could not grow.** Runtime handles `Axes`, `Button`, `TextBox`; the
designer can only *create* `Axes` and `Button`. `get_content()` raises `NotImplementedError` for
everything else (`function_templates.py:10-11, 77-78`). Radio buttons, checkboxes, dropdowns, lists,
labels, sliders — all named as core to the paradigm — were not merely unfinished, they were
unreachable: matplotlib has no dropdown, no list box, no real label.

**S1b — performance collapsed as controls were added.** matplotlib was never designed to host many
widgets in one figure, and it is inefficient at it. Each added control made the interface measurably
slower, and the degradation compounds exactly as an interface becomes useful. An iteration tool that
gets sluggish as your interface grows defeats its own purpose.

Both failures dissolve under one correction: **matplotlib draws plots; Tk provides every control.**
See K7 and R3.

### S2. Hot reload was never wired, and the current design prevents it

Handlers are resolved **once**, at startup, and cached in a dictionary
(`user_gui_aux.py:34, 46, 53, 69`). Editing the research file afterwards has no effect, because the
cached function objects still point at the old code.

The fix is *not* necessarily to resolve at every invocation. R2 requires only that the binding table be
refreshable without restarting the process — re-resolving when the layout changes, which is
infrequent, may well be enough. When the refresh happens is an open design question (Q1).

### S3. "No code behind this control" and "the code is broken" are indistinguishable

This one needs care, because the spike's *behavior* here is right and only its *diagnosis* is wrong.

Four bare `except:` clauses (`user_gui_aux.py:33-37, 45-49, 51-56, 68-72`) wrap the handler lookup and
fall back to a no-op lambda. Falling back to a no-op is **correct and required** (W5, commitment #4) —
a control the researcher has not written code for yet must not crash the process. Letting it crash
would break the entire point of quick iterative design: you want to fix the code *without* tearing down
and restarting the Python process.

The flaw is narrower. A bare `except:` catches *everything*, so two very different situations produce
an identical silent outcome:

| Situation | Right response |
|---|---|
| The handler is genuinely not defined | Continue. Normal and expected — optionally a quiet note. |
| The module failed to import, or raised — syntax error, bad import, exception at import time | Continue **and tell the researcher what broke**, with the traceback. |

Today the second case looks exactly like the first: you click, nothing happens, no message anywhere,
and the researcher has no idea their file has a syntax error. Three of the four clauses do not even
warn — the warning line is commented out.

The correction is to separate the two cases (an `AttributeError` from the lookup means "not defined";
anything else means "the code is broken"), report the second visibly, and **keep running in both**.
See R1.

### S4. Editing and running are separate modes — real, and possibly not fully solvable

`edit_gui()` opens a Tk window; `run_gui()` opens a pyplot window. You switch between them by
commenting and uncommenting lines in `__main__` (`example1.py:57-59`). A script runs in edit mode or in
run mode, never both. Adding a control to an interface you are actively using means stopping,
switching mode, drawing, and restarting.

This is a genuine cost, and it is **not assumed to be solvable**. Commitment #3 already concedes that
visual edits may require a relaunch. How much of the cost can be recovered needs to be thought
through — see Q2. This is explicitly *not* a constitution rule.

### S5. Two different GUI stacks, neither owned

The designer is tkinter hosting an embedded matplotlib canvas (`gui_maker.py:25-39`). The runtime is a
bare `plt.figure()` with no tkinter shell (`user_gui_aux.py:80`). Two window models, two event paths,
and consequently no shared rendering of what a control actually looks like. With Tk now decided for
both (K7), the two must share one stack.

### S6. *(Reclassified — not a design defect)*

Earlier flagged as "file resolution depends on the working directory." The convention is deliberate and
fine: **the `.yaml` and the `.py` share a basename and sit in the same folder**, and the interface is
addressed by that shared name. That is a keeper, recorded as K8.

The only residual nit: `f'{name}.yaml'` and `import_module(name)` (`user_gui_aux.py:76, 81`) resolve
against the *current working directory* rather than the folder the pair lives in, so launching from
elsewhere breaks a pair that is otherwise correctly colocated. Narrow fix, no design impact — R6.

### S7. Property editing is almost absent, and the layout schema cannot hold properties anyway

The properties sidebar appears only for Buttons and exposes only `tag` and `label`
(`gui_maker.py:105, 370`). No way to edit window size, axis titles, colors, fonts, or initial values.

The deeper problem is underneath it: **the layout schema was never rich enough.** Every element carries
a type, a unique name, and a position — and essentially nothing else. That is not enough to hold the
ever-growing property set a real interface needs: font, font size, text color, background color, edge
color, border width, cursor icon, enabled/disabled, tooltip, tab order, and more.

The evidence that this had already begun to bite: the runtime reads `color`, `hovercolor`, `label_pad`,
and `textalignment` for a TextBox (`user_gui_aux.py:26-30`), but the designer cannot write any of
them — so a TextBox created in the designer crashes the runtime with a `KeyError`. The two sides had
already drifted apart at three widget types.

YAML as the *file format* is still right (K1). The *schema* has to be redesigned: extensible per-type
property blocks, sane defaults so a minimal element stays terse, and a schema version so it can evolve.

### S8. Direct manipulation is one element at a time

No undo, no multi-select, no alignment guides or snapping, no keyboard nudge, no z-order, no duplicate.
Every position is set by free-hand dragging and rounded to two decimals (`gui_maker.py:428-433`).

### S9. Deleting an element orphans its handler

`delete_gui_element` removes the entry from the layout file and leaves the handler in the code file
(`gui_maker.py:404-407`). The trade-off is correct — never destroy the researcher's code — but there is
no notice, no list of orphans, no assisted cleanup. Contrast with rename, where the decision goes the
other way (K10).

### S10. Runtime state is written back into the layout data

`make_axes` stores a live widget handle inside the dictionary loaded from the layout file
(`user_gui_aux.py:42`). The in-memory layout is therefore no longer serializable, which quietly rules
out ever saving layout changes from the running interface.

### S11. Prototype hygiene

`print_debug = True` with debug prints on hot paths; two `if False:` blocks preserving an abandoned
in-canvas toolbar (`gui_maker.py:282-316`); `eval()`-based dispatch (`gui_maker.py:340-343`); large
commented-out regions; a stray `select_callback` defined without `self` (`gui_maker.py:248`); dead
module-level `on_startup` / `on_submit_txt1` (`gui_maker.py:418-423`); the generated launcher still
imports the long-dead name `EZplt` (`function_templates.py:59-60`), so generated code does not run.

Also worth settling: the environment object is called `ez` in the runtime (`user_gui_aux.py`) but the
generated stubs name the same parameter `ev` (`function_templates.py:14, 20, 31`). Two names for one
thing, in the two places the user actually reads. Per W3 the name is `ev` — apply it everywhere.

### S12. No tests, empty README

`README.md` contains one line: the project name.

---

## 4. Decisions

### 4a. Carried over from the spike

| # | Decision | Why it earned its place |
|---|---|---|
| K1 | **YAML as the layout file format** | Human-readable, diffable in version control, hand-editable when the designer cannot express something. Note the scope: the *format* is kept, the *schema* is redesigned (S7). |
| K2 | **Normalized [0,1] positions** | Resolution independence for free; window resize is not a special case. |
| K3 | **AST parsing to detect existing handlers** | Robust to reformatting, comments, and decorators in a way regex is not. Port the technique. |
| K4 | **Naming-convention binding** (`on_<event>_<name>`) | Zero registration boilerplate — the researcher writes a function and it is wired. Keep the convention; change *when* it is resolved (R2). |
| K5 | **One environment object, named `ev`, as first parameter to every handler** | Solves cross-handler state without globals. Direct descendant of MATLAB's `handles`, and the right ancestor. Two letters because it gets typed constantly. |
| K6 | **Additive-only code generation** | The researcher's code is sacred — with one sanctioned exception, rename (K10). |
| K8 | **A `.yaml` / `.py` pair sharing a basename in one folder, addressed by that name** | The entire configuration story is "what is it called". Nothing to wire up, nothing to register. |
| K9 | **One command to edit, one command to run; editing a name that does not exist creates it blank** | No project scaffolding, no ceremony. Idea to drawable canvas in one line. |

### 4b. Settled during this review (2026-09-07)

| # | Decision | Rationale |
|---|---|---|
| K7 | **Tk is the GUI toolkit. matplotlib is used only to render plots, inside embedded canvases.** Every control is a Tk widget; no control is ever a `matplotlib.widgets` widget. | Corrects S1 in both of its halves — the vocabulary cap and the performance collapse. Tk is in the standard library, serving the goal of minimal dependencies and minimal complexity. |
| K10 | **Renaming an element renames its handlers in the Python file too.** | The one deliberate exception to K6. Leaving the researcher to hand-fix broken name links would be the opposite of making life easy, and rename is unambiguous enough to automate safely. |
| K11 | **Reload discards nothing.** Memory, the environment object and everything in it, loaded data, computed results, and plots already drawn all persist. Only the code of the handler being invoked is reloaded. | This is what makes commitment #3 worth having: expensive data loading happens once per session, not once per edit. It also sharply narrows what reload has to do. |

---

## 5. Rules — candidates for the constitution

- **R1** — The process never dies because of the researcher's code. A control with no handler is a
  no-op; a handler whose module is broken or which raises is reported visibly, with the traceback, and
  the interface stays alive and usable. **Never crash, always tell.** Fixing the code must never
  require restarting the Python process. *(from S3, commitment #4)*
- **R2** — Handlers are never permanently bound at startup. The binding table must be refreshable
  without restarting the process. *When* it refreshes — every invocation, on layout change, on file
  change, on demand — is a design choice (Q1), not fixed by this rule. *(from S2)*
- **R3** — matplotlib renders plots and only plots. Every interactive control is a Tk widget. No
  control is ever implemented as a `matplotlib.widgets` widget, whatever the short-term convenience.
  *(from S1, K7)*
- **R4** — Generated edits to the researcher's code file are additive: no deletion, no rewriting, no
  reordering of code the researcher wrote. The sole exception is rename (K10), which rewrites handler
  names and nothing else. Writes are atomic (write-temp-then-replace), never an in-place re-write of an
  open handle. *(from K6, and `gui_maker.py:507-522`)*
- **R6** — A project's files resolve relative to the folder holding the `.yaml`/`.py` pair, never
  relative to the current working directory. *(from S6)*
- **R7** — The designer and the runtime share one layout schema. Every property the runtime reads must
  be writable in the designer, and every property the designer writes must be understood by the
  runtime. The schema is versioned and extensible per element type, with defaults so a minimal element
  stays terse. *(from S7)*

*(R5 — "designing and running must not be separate programs" — was withdrawn. See S4 and Q2: it is a
cost to be reduced, not a rule to be enforced.)*

---

## 6. Reusable assets

Specific things worth lifting rather than re-deriving. All paths relative to `reference/legacy-rrGUI/`.

| Asset | Path | Condition |
|---|---|---|
| Layout schema seed | `example1.yaml` | A shape reference only. The schema itself is being redesigned (S7, R7). |
| Coordinate converters | `src/rrGUI/gui_maker.py:425-440` | Small and correct. Port nearly as-is. |
| AST additive-insert logic | `src/rrGUI/gui_maker.py:202-224, 497-505` | Port the *logic*. Replace `write_content` (`:507-522`) — it re-writes a file through an open read-write handle with no temp file, which can corrupt the researcher's code on interruption. The same AST machinery is the basis for rename (K10). |
| Stub templates and their voice | `src/rrGUI/function_templates.py` | The generated comments' tone is genuinely good. The `EZplt` reference at `:59-60` is dead and must not be copied. |
| Environment-object shape | `src/rrGUI/user_gui_aux.py:9-22` | The dataclass skeleton; drop `add_attr` / `get_attr` in favor of normal attribute access. |
| Working example | `example1.py` + `example1.yaml` | The clearest statement of the developer experience the product aims at. Useful as an acceptance fixture. |

---

## 7. Open questions

Good candidates for `/speckit-clarify`.

1. **What triggers handler re-resolution?** R2 requires only that the binding table be refreshable.
   Options: re-resolve on every invocation; re-resolve when the layout changes (infrequent and cheap);
   watch the `.py` file's modification time; an explicit reload control; re-resolve when the window
   regains focus. The trade-off is per-click overhead against how stale a binding may get.
2. **How much of the edit/run mode split can be recovered?** (S4) Full unification may not be
   achievable. Intermediate options worth weighing: a relaunch that automatically restores session
   state; a designer that operates on a live interface for position and size only; or accepting the
   split and making the round-trip near-instant.
3. **What is the v1 widget vocabulary?** Named so far: plot axes, buttons, radio buttons, text boxes,
   labels, lists, dropdowns. Which are P1 for a first usable release, now that Tk removes the ceiling?
4. **How is the property schema structured?** (S7, R7) Which properties are universal versus per-type,
   how are defaults expressed so simple elements stay terse, and how does the schema version and
   migrate as properties are added?
5. **One window, or many?** Research interfaces grow. Tabs, panels, multiple windows, dockable plots?
6. **What happens during a long computation?** Does a click block the interface? Threading is where
   most iterative-GUI tools break down, and the spike never ran anything slow enough to find out. This
   interacts with R1: an exception on a worker thread still has to reach the researcher.
7. **Is the environment object the only state channel?** Does anything persist between sessions — last
   file opened, last control values, window geometry?
8. **Does a finished interface get shared?** Can a colleague run it without the designer? Is there a
   packaging story, or is this strictly a personal development tool?
9. **Is `iterlab` the final name?** Third name for this idea (`EZplt`, `rrGUI`, `iterlab`).

### Resolved during review

| Question | Answer |
|---|---|
| Which GUI toolkit? | **Tk**, for minimal dependency and minimal complexity. matplotlib for plots only. → K7, R3 |
| What survives a reload? | **Everything.** Memory, data, and already-drawn plots are untouched; only the invoked handler's code is refreshed. → K11 |
| What happens on rename? | **Rename the handlers in the Python file too** — make life easy for the user. Deliberate exception to additive-only. → K10 |
| Is the no-op fallback for missing handlers a defect? | **No, it is required.** Only the conflation of "not defined" with "code is broken" is the defect. → S3, R1 |
| Is cwd-relative file resolution a design problem? | **No** — the same-name, same-folder pair is the intended convention. Narrow bug only. → K8, R6 |

---

## 8. Routing into Spec Kit

| Section | Feeds |
|---|---|
| 1. Intent, 2. What worked | `/speckit-specify` |
| 5. Rules, 4. Decisions | `/speckit-constitution` |
| 7. Open questions | `/speckit-clarify` |
| 4. Decisions, 6. Reusable assets | `/speckit-plan` |
| 3. Where it stalled | Read before all of the above; it is the argument for the rules |
