# Feature Specification: End-to-End Minimal Loop

**Feature Branch**: `001-end-to-end-loop`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: *(none supplied with the command)* — feature selected interactively as
"End-to-end minimal loop": the thinnest slice that is genuinely the paradigm. Draw a plot area and a
button, run the interface, click it, edit the algorithm, and see the change without restarting or
reloading data. Narrow in element types, complete in flow.

## Clarifications

### Session 2026-09-07

- Q: Which interactions should each element type respond to in this first feature? → A: The event set
  is universal, not per-type. Every element can potentially respond to click, hover, move, and keyboard
  key, and a click handler can tell which mouse button was used. All of these are *optional* — a
  researcher gets behavior only for the handlers they actually write. What differs per element type is
  the **default handler**, the one stub generated automatically on creation: for a button it is click,
  for a plot area it is click. Plot areas additionally provide the standard plotting toolbar (pan,
  zoom) without any handler being written. For text boxes, when they arrive in a later feature, the
  default is "the text was committed" — on Enter or on leaving the field, never on every keystroke.
- Q: When a code edit is picked up, should the researcher's startup code run again? → A: Never
  automatically. Picking up a code change refreshes handler behavior only; startup is not re-run, so
  loaded data is never silently discarded.
- Q: *(revised after clarification)* What if the researcher edits the startup code itself? → A:
  Startup runs on startup. Changing it takes effect by starting a fresh session — see the revision
  session below, where the mode toggle makes that a single click — and no in-session re-run is
  offered — running setup again over a populated session risks double-opening connections and
  double-registering callbacks. The one exception is a startup that never completed successfully,
  which is attempted again once the code loads; that is a deferred first run rather than a re-run,
  and it is what lets a researcher recover from a typo in startup without relaunching.
- Q: Should a researcher be able to choose an element's name, and to change it later? → A: Name it at
  creation, with a sensible default pre-filled so it can simply be accepted. ~~Renaming an existing
  element is deferred to a later feature.~~ **Superseded below** — the properties panel makes the name
  editable, so renaming is in scope after all.
- Q: When the researcher resizes the interface window, how should elements behave? → A: Element
  geometry — position and size — scales proportionally with the window, so the layout as drawn is
  always the layout as rendered. Text is exempt and renders at a fixed readable size at any window
  size. Per-element control over scaling is deferred; it can be added later as a compatible addition
  because the default preserves this behavior.
- Q: Should the layout file record which schema version wrote it, starting with this first release? →
  A: Yes — the version is recorded from the first release, because it is the one thing that cannot be
  added retroactively to files already written. Migration code is deliberately not built now; it is
  written when the first schema-breaking change is actually made, against a real case rather than a
  speculative one. A layout written by a newer version is reported and left unopened rather than
  partially understood.

### Session 2026-09-07 (revision: one program, two modes)

- Q: Should editing the layout and using the interface be one program or two? → A: **One program, one
  command.** A toggle in the top-left corner switches between editor mode and GUI mode. The researcher
  never edits Python and never runs a different command to switch. This reverses the earlier assumption
  that editing and running are separate activities.
- Q: When toggling from editor mode back to GUI mode, does the running session survive? → A: Not in
  this feature. Toggling to the editor ends the session; toggling back starts a fresh one and runs
  startup again. Applying layout edits to a live session with data and plots preserved is recorded as
  the **aim**, not promised, because it has not been attempted yet.
- Q: Which mode does the single command open in? → A: Editor mode when the interface has no elements
  yet, GUI mode when it has. A new interface opens where the researcher has to start anyway, and an
  existing one opens ready to use.
- Q: What can the properties panel edit? → A: For a button — position, name, and label. For a plot area
  — position and name. All are editable, including the name, so **renaming is in scope**, superseding
  the earlier deferral. Geometry can be typed as numbers instead of dragged, for when precision matters
  more than speed.
- Q: How is a graphical tool verified before release? → A: Automatically wherever possible, plus a
  recorded manual checklist worked through by the maintainer for what genuinely cannot be automated.
  Both are release gates.

## User Scenarios & Testing *(mandatory)*

The actor throughout is a **researcher** — an engineer or scientist developing an algorithm, who is
comfortable writing analysis code but is not a GUI programmer and does not want to become one.

### User Story 1 - Draw an interface and use it, in one program (Priority: P1)

A researcher wants to try an idea that needs a plot and a button. They run one command naming an
interface that does not exist yet. A window opens in **editor mode**: a blank canvas, and a sidebar
holding a palette of the element types they can add and a properties panel for whatever is selected.

They pick "plot area" from the palette and drag out a rectangle. The properties panel fills in with a
name already suggested, which they change to `spectrum`. They pick "button", drag a smaller rectangle,
name it `run_fit`, and type "Run fit" as its label. The code file now holds one empty, clearly
commented handler for each, and nothing else in it has changed.

They click the toggle in the top-left corner. The window becomes **GUI mode** — their plot area and
their button, laid out as drawn. They click the button and their code runs. One more click and they
are back in the editor, moving things around.

At no point did they write, read, or edit any layout code. At no point did they edit Python, run a
different command, or restart anything in order to move between building the interface and using it.

**Why this priority**: Nothing else in the product is reachable without this. It is also the first
moment a researcher sees the paradigm work — a functioning graphical interface they never programmed —
and by itself it already replaces the write-run-close-edit-rerun cycle for simple cases. The single
command and the toggle matter as much as the drawing: a researcher who must stop and edit a launcher
in order to move a button has been handed back exactly the ceremony this project exists to remove.

**Independent Test**: A researcher who has never used the tool is given only its name, and asked to
produce a window with a working button and then to move that button — without ever leaving the
program. Fully testable with no other story built.

**Acceptance Scenarios**:

1. **Given** no interface named `demo` exists, **When** the researcher runs the single command naming
   `demo`, **Then** a window opens in editor mode with a blank canvas, and both a layout file and a
   starter code file are created for it.
2. **Given** a blank canvas, **When** the researcher chooses a type from the palette and drags out a
   region, **Then** the element appears on the canvas and the properties panel shows its properties
   with a usable default name already filled in.
3. **Given** the researcher has drawn a button, **When** the element is created, **Then** the code file
   contains a handler for that button that did not previously exist, and no other part of the file has
   changed.
4. **Given** an interface in editor mode with a plot area and a button, **When** the researcher clicks
   the toggle, **Then** the window switches to GUI mode showing both elements positioned as drawn.
4a. **Given** an interface in GUI mode, **When** the researcher clicks the toggle, **Then** the window
    returns to editor mode with the canvas, palette, and properties panel.
4b. **Given** an interface that already has elements, **When** the researcher runs the single command,
    **Then** it opens directly in GUI mode rather than the editor.
4c. **Given** an interface with no elements, **When** the researcher runs the single command, **Then**
    it opens in editor mode.
4d. **Given** either mode, **When** the researcher looks at the top-left corner, **Then** the toggle is
    visible and is never obscured by any element they have drawn.
5. **Given** a running interface, **When** the researcher clicks the button, **Then** the handler in
   their code file executes.
6. **Given** a handler that draws into the plot area by its assigned name, **When** it executes,
   **Then** the drawing appears in that plot area.
7. **Given** the researcher has drawn a button but written no code for it, **When** they click it,
   **Then** nothing happens and the session continues normally.
8. **Given** a running interface, **When** the researcher resizes the window, **Then** every element
   keeps its proportional position and size, and all text remains at the same readable size it had
   before.
9. **Given** a plot area containing a drawing and no handlers written for it at all, **When** the
   researcher uses the standard plotting toolbar, **Then** they can pan and zoom the plot.
10. **Given** an element type whose default interaction is a click, **When** the element is created,
    **Then** exactly one handler stub is generated for it and no stubs are generated for hover, move,
    or keyboard.

---

### User Story 2 - Change the algorithm without restarting (Priority: P2)

The researcher's interface is running. On startup it loaded a large dataset — slow enough to be
annoying — and their plot area shows a first result. The result is wrong. They switch to their editor,
change the handler, save, switch back, and click the button again. The new version of their code runs.
The dataset was never reloaded. The plot from before is still there until their code replaces it.

They repeat this twenty times in ten minutes.

**Why this priority**: This is the paradigm's central economic claim and the reason the tool exists.
Story 1 without this is a pleasant way to build a GUI; Story 1 with this is a different way to develop
algorithms. It is deliberately second only because it has nothing to attach to until Story 1 exists.

**Independent Test**: Load data that takes a noticeable time to load, plot it, edit the handler, and
re-trigger. Verify the new behavior runs and that the load did not repeat. Measurable with a stopwatch.

**Acceptance Scenarios**:

1. **Given** a running interface whose startup loaded data into the session environment, **When** the
   researcher edits a handler and re-triggers it, **Then** the edited version executes.
2. **Given** the same situation, **When** the edited handler executes, **Then** the previously loaded
   data is still available to it and was not reloaded.
3. **Given** a plot area containing a drawing, **When** the researcher edits unrelated code and
   re-triggers a different element, **Then** the existing drawing remains on screen.
4. **Given** a running interface, **When** the researcher adds a brand-new handler for an element that
   previously had none, **Then** that element becomes functional without relaunching.
5. **Given** a researcher edits code but does not re-trigger anything, **When** they then interact with
   an unrelated element, **Then** that element behaves according to the current state of the code file.
6. **Given** a researcher has saved an edit, **When** they next interact with the interface, **Then**
   the edit is already in effect without their having pressed, selected, or configured anything.
7. **Given** a researcher interacts repeatedly without editing anything in between, **When** each
   interaction occurs, **Then** their code is not reapplied and any startup-level work is not repeated.
8. **Given** a running interface with data loaded at startup, **When** the researcher edits the startup
   code itself and then interacts with the interface, **Then** the data loaded earlier is still intact
   and the startup code has not been re-run.
9. **Given** the researcher has edited the startup code, **When** they want that change to take effect,
   **Then** starting a fresh session applies it — by relaunching, or simply by toggling to editor mode
   and back — and there is no way to re-run startup within a live session.
10. **Given** an interface launched while its startup code was broken, so startup never completed,
    **When** the researcher fixes the code and interacts with the interface, **Then** startup runs for
    the first time and the session becomes usable without relaunching.

---

### User Story 3 - Keep working when the code is broken (Priority: P3)

Mid-iteration, the researcher saves a file with a typo. They click the button. The window stays open.
A clear report tells them what is wrong and where. They fix the typo, save, click again, and continue
— same session, same loaded data, no relaunch.

Separately, they draw a third element intending to write its code later. Clicking it does nothing, and
nothing is reported, because there is nothing wrong.

**Why this priority**: Stories 1 and 2 describe the happy path; this describes the path a researcher is
actually on for much of a session. Without it, the first typo forces the restart that Story 2 exists to
eliminate, and the value of Story 2 collapses in real use. It is third only because it cannot be
demonstrated before there is something to break.

**Independent Test**: Introduce a syntax error, an import failure, and a runtime exception in turn.
Verify in each case that the session survives, the researcher is told what happened, and recovery
requires only fixing the code.

**Acceptance Scenarios**:

1. **Given** a running interface, **When** the researcher's code file contains a syntax error and they
   trigger any element, **Then** the session remains open, full detail appears in their textual output,
   and the window itself shows which element failed and why.
2. **Given** the same situation, **When** the researcher corrects the error and re-triggers, **Then**
   the corrected code runs in the same session with all prior data intact, and the in-window signal
   clears.
3. **Given** a handler that raises an error while running, **When** it is triggered, **Then** the
   session remains open and the report identifies the failure and the point in the researcher's code
   where it occurred.
4. **Given** an element with no handler written for it, **When** it is triggered, **Then** nothing
   happens and no error is reported — this is a normal, expected state.
5. **Given** a code file that is broken at the moment the interface is first launched, **When** the
   researcher launches it, **Then** the interface still opens and the problem is reported.
6. **Given** a fault is being displayed in the window, **When** the researcher interacts with a
   different, working element, **Then** it works normally and nothing had to be dismissed first.

---

### User Story 4 - Refine elements without disturbing the code (Priority: P4)

Two weeks and four hundred lines later, the researcher wants the plot bigger and needs a second button.
They toggle into the editor, drag the plot area larger, nudge the first button, and draw a second one.
Selecting the plot area, they see its properties and type exact numbers for its position rather than
fighting to align it by hand. They also realize `axes_0` was a poor name and change it to `spectrum` —
and the handler in their code file is renamed to match, with nothing else touched.

They toggle back. The layout has changed, their four hundred lines are as they left them apart from the
renamed handler and one new empty stub, and everything still works.

**Why this priority**: This is what makes the paradigm survivable past the first hour — but it is the
last of the four to become necessary, because it only matters once there is code worth protecting.

**Independent Test**: Take an interface with substantial hand-written code, make several layout and
property changes including a rename, and compare the code file before and after. The only differences
may be appended stubs and the renamed handler.

**Acceptance Scenarios**:

1. **Given** an interface with existing hand-written handlers, **When** the researcher moves and resizes
   elements, **Then** the code file is byte-for-byte unchanged.
2. **Given** the same interface, **When** the researcher adds a new element, **Then** exactly one new
   stub is appended and no existing content is modified, reordered, or removed.
3. **Given** an interface previously edited, **When** the researcher returns to editor mode, **Then**
   all existing elements appear at their saved positions and sizes.
4. **Given** an element that already has a handler, **When** the layout is edited and saved again,
   **Then** no duplicate handler is created.
5. **Given** the researcher deletes an element, **When** they toggle to GUI mode, **Then** the element
   is gone from the window and its handler remains untouched in the code file.
6. **Given** an element is selected, **When** the researcher types new numbers into its position
   fields, **Then** the element moves to exactly those coordinates on the canvas.
7. **Given** a button is selected, **When** the researcher edits its label, **Then** the displayed text
   changes and neither the element's name nor any handler is affected.
8. **Given** an element named `axes_0` with a handler `on_clicked_axes_0`, **When** the researcher
   renames it to `spectrum`, **Then** the handler becomes `on_clicked_spectrum` and **nothing else in
   the code file changes**.
9. **Given** a rename, **When** the researcher had also written other handlers for the same element,
   **Then** all of them are renamed together, and handlers belonging to other elements are untouched.
10. **Given** the researcher types a name that is not usable in code, or one already in use, **When**
    they attempt to apply it, **Then** it is rejected with an explanation and nothing is renamed.
11. **Given** the code file does not currently parse, **When** the researcher attempts a rename,
    **Then** it is refused and reported, and the file is left exactly as it was.

---

### Edge Cases

- **Opening a name that does not exist** — treated as creation, not as an error. Both files appear.
- **An interface with no elements at all** — opens as an empty window without complaint.
- **An element drawn overlapping another** — permitted; both remain addressable and independently
  clickable according to their stacking.
- **A layout file that has been hand-edited into an invalid state** — reported clearly, identifying what
  is wrong, rather than failing obscurely or silently discarding the file.
- **A layout written by a newer version of the tool** — recognized as such and reported, naming what
  the researcher needs to do. The file is left exactly as it is: not opened, not partially applied,
  and above all not written back, since saving it would discard whatever the newer version had
  recorded.
- **A window resized to an extreme aspect ratio** — elements keep their proportions and text stays
  readable; nothing is clipped away without the researcher being able to restore it by resizing back.
- **Two elements given the same name** — prevented at the point of naming; names are unique within an
  interface.
- **A handler the researcher deletes after it was generated** — the element reverts to doing nothing;
  no error, no regeneration on the next layout edit unless the element is recreated.
- **A code file the researcher has reformatted or reorganized** — stub detection still recognizes
  existing handlers, and does not duplicate them.
- **A name that would not work in code** — rejected when typed, with an explanation, rather than
  accepted and producing a broken handler later.
- **Wanting a different name after the fact** — supported. Renaming through the properties panel
  rewrites the element's handlers to match and touches nothing else in the code file.
- **Renaming while the code file is broken** — refused and reported, with the file untouched. A rename
  cannot be performed safely on a file that will not parse.
- **Renaming an element that has no handlers yet** — succeeds; there is simply nothing in the code file
  to rename.
- **An element drawn beneath the mode toggle** — permitted, but the toggle stays on top and remains
  clickable. Editor mode shows the toggle's footprint so this can be avoided deliberately.
- **Toggling with unsaved work** — cannot arise: layout changes are persisted as they are made, so a
  mode switch never risks losing an edit.
- **A handler that runs for a long time** — the interface is unresponsive while it runs. Accepted for
  this feature; see Assumptions.
- **An interface left running while its layout is edited elsewhere** — the running window continues to
  reflect the layout it was launched with.
- **Interruption partway through writing the code file** — the researcher's file is never left
  truncated or corrupted.

## Requirements *(mandatory)*

### Functional Requirements

**Creating and editing an interface**

- **FR-001**: A researcher MUST be able to open an interface using a **single command** that names it,
  with no other setup, registration, or configuration step. There MUST NOT be separate commands for
  editing and for using an interface.
- **FR-001a**: An interface with no elements MUST open in editor mode; an interface that has elements
  MUST open in GUI mode.
- **FR-002**: Opening an interface that does not yet exist MUST create it — a blank layout and a
  starter code file — rather than reporting an error.
- **FR-003**: The system MUST allow elements to be created by direct manipulation — choosing a type and
  dragging out a region on a canvas — and MUST NOT require any layout code to be written.
- **FR-003a**: Editor mode MUST present a palette of every element type that can be added, so that the
  available vocabulary is discoverable without documentation.
- **FR-004**: The system MUST support two element types in this feature: a **plot area** and a
  **button**.
- **FR-005**: Every element MUST have a name that is unique within its interface. The system MUST
  prevent duplicates.
- **FR-005a**: The researcher MUST be able to set an element's name at the moment they create it. A
  usable default MUST be pre-filled so that accepting it requires no typing.
- **FR-005b**: A name MUST be valid for use in the researcher's code, since it becomes part of a
  handler's name and is used to reach the element. Names that would not be usable there MUST be
  rejected at the point of entry, with an explanation, rather than accepted and failing later.
- **FR-005c**: The researcher MUST be able to rename an element after creation, through the properties
  panel.
- **FR-005d**: Renaming an element MUST rename **every** handler belonging to it in the researcher's
  code file, and MUST change nothing else in that file. Handlers belonging to other elements MUST NOT
  be touched.
- **FR-005e**: A rename MUST be rejected, with an explanation and no change made, if the new name is
  not usable in code (FR-005b) or is already in use by another element.
- **FR-005f**: If the code file does not currently parse, a rename MUST be refused and reported, and
  the file MUST be left exactly as it was. Renaming by guesswork on an unparseable file is prohibited.
- **FR-006**: The system MUST allow existing elements to be moved and resized by direct manipulation,
  and MUST allow them to be deleted.
- **FR-006a**: Editor mode MUST present a properties panel showing the properties of the currently
  selected element, and MUST indicate when nothing is selected.
- **FR-006b**: The properties panel MUST expose, for a **button**: position, name, and label. For a
  **plot area**: position and name. Every one of these MUST be editable.
- **FR-006c**: Any property that can be set by dragging MUST also be settable as a typed value, so that
  exact alignment does not depend on a steady hand. A value typed into the panel and a change made by
  dragging MUST produce identical results.
- **FR-006d**: A change made in the properties panel MUST be reflected on the canvas immediately, and a
  change made on the canvas MUST be reflected in the panel immediately.
- **FR-006e**: An invalid property value MUST be rejected with an explanation, leaving the element as
  it was. The panel MUST NOT accept a value it will silently discard.
- **FR-007**: Element positions and sizes MUST be preserved across editing sessions and MUST be
  reproduced faithfully when the interface is run.
- **FR-008**: Layout changes MUST be persisted without the researcher taking an explicit save action.

**The link between layout and code**

- **FR-009**: Creating an element MUST append exactly one handler — that element type's default
  handler per FR-017d — to the researcher's code file, commented to explain what it does and that it
  may be deleted. Stubs for the other available interactions MUST NOT be generated.
- **FR-010**: The system MUST NOT delete, rewrite, reorder, or otherwise modify any content the
  researcher wrote in their code file. There is exactly one exception: renaming handlers when their
  element is renamed (FR-005c, FR-005d). That exception **is** exercised in this feature, and it is
  the only code path permitted to modify existing lines. It MUST change handler names and nothing
  else — not formatting, not ordering, not surrounding code.
- **FR-011**: The system MUST detect handlers that already exist and MUST NOT duplicate them, including
  when the researcher has reformatted or reorganized the file.
- **FR-012**: Deleting an element MUST NOT delete its handler.
- **FR-013**: Writes to the researcher's code file MUST be atomic — an interruption at any point MUST
  leave the previous contents intact rather than a partial file.
- **FR-014**: Moving, resizing, or restyling an element MUST produce no change whatsoever to the code
  file.

**Running an interface**

- **FR-015**: The researcher MUST be able to switch between editor mode and GUI mode by a single
  action from within the interface itself — a toggle in the top-left corner — without editing Python,
  running a different command, or leaving the program.
- **FR-015a**: The toggle MUST be present and operable in **both** modes.
- **FR-015b**: The toggle MUST be rendered above every element and MUST NOT be obscured by anything the
  researcher draws. Editor mode MUST make its footprint visible so a researcher can choose not to place
  something important beneath it.
- **FR-015c**: The toggle and the editor sidebar are application chrome, not layout. They MUST NOT
  appear in the layout file, MUST NOT be movable or deletable by the researcher, and MUST NOT be
  reachable from the researcher's code as elements.
- **FR-015d**: A session MUST belong to the interface rather than to GUI mode, and MUST survive any
  number of mode switches. Switching modes MUST preserve session state, anything drawn on a plot area,
  and the fact that startup has already run. Widgets are destroyed with the mode that built them and
  rebuilt on return; the element handles reached through the session object are rebound to the new
  widgets, and no other session state is discarded.
  *(Amended after implementation. This originally said the opposite — that a switch ended the session.
  That did not remove the cost of reloading data, it moved it from "every code edit" to "every layout
  edit", which contradicts the purpose the toggle exists to serve.)*
- **FR-015e**: Because a mode switch no longer restarts anything, there MUST be exactly one explicit
  control that discards the session and begins again, and it is the only supported way to apply a
  change to the startup code without leaving the program (see FR-026c). It MUST be application chrome
  under FR-015c, and MUST be inoperable in editor mode, where there is no live session to discard.
- **FR-015f**: State belonging to an element deleted while in editor mode MUST be discarded on the
  next switch to GUI mode. State belonging to a renamed element MUST follow the new tag.
- **FR-016**: The system MUST present a window containing every element in the layout, positioned as
  drawn.
- **FR-017**: Interacting with an element MUST invoke its correspondingly named handler if one exists.
- **FR-017a**: The set of interactions MUST be universal across element types, not specific to any one
  type. Every element MUST be able to respond to **click**, **hover**, **move**, and **keyboard key**.
- **FR-017b**: Every handler MUST be optional. An element responds to exactly those interactions the
  researcher has written handlers for, and to no others; the absence of a handler is never an error
  (see FR-029).
- **FR-017c**: A click handler MUST be able to determine which mouse button was used.
- **FR-017d**: Each element type MUST define exactly one **default handler** — the single stub
  generated when an element of that type is created. In this feature the default is **click** for a
  button and **click** for a plot area. Handlers for the other interactions are written by the
  researcher when wanted, and are never generated unasked.
- **FR-017e**: A plot area MUST provide the standard plotting toolbar behaviors — at minimum pan and
  zoom — without the researcher writing any handler for them. These MUST NOT consume interactions in a
  way that prevents the researcher's own handlers from running when the toolbar is not in use.
- **FR-018**: Every handler MUST receive a single session environment object as its first argument,
  through which the researcher stores and retrieves data across interactions without using globals.
- **FR-019**: Every element MUST be reachable from that environment object under the same name shown in
  the editor.
- **FR-020**: The system MUST run researcher-supplied startup code once when the interface launches,
  before any interaction is possible.
- **FR-021**: Element positions MUST be expressed such that the interface renders correctly regardless
  of window size or display resolution.
- **FR-021a**: When the window is resized, element geometry — both position and size — MUST scale
  proportionally, so that the arrangement the researcher drew is always the arrangement they see.
- **FR-021b**: Text MUST be exempt from that scaling and MUST render at a fixed readable size at every
  window size. This applies to control labels and to text drawn as part of the interface chrome.
- **FR-021c**: Per-element control over scaling behavior is out of scope for this feature. Any later
  addition of it MUST default to the behavior in FR-021a and FR-021b, so that existing layouts are
  unaffected.

**Iterating without restarting**

- **FR-022**: A change to the researcher's code MUST take effect without relaunching the interface and
  without ending the session.
- **FR-023**: Applying a code change MUST NOT discard anything held in the session — loaded data,
  computed results, and the contents of the session environment MUST all survive.
- **FR-024**: Applying a code change MUST NOT clear or redraw plot areas. Existing drawings persist
  until the researcher's own code replaces them.
- **FR-025**: A handler added to the code file after the interface was launched MUST become effective
  without relaunching.
- **FR-026**: The system MUST check, at the moment of each interaction, whether the researcher's code
  has changed since it was last loaded, and MUST apply the change before invoking the handler. The
  researcher MUST NOT have to take any action to make an edit take effect — no reload control, no
  restart, no explicit signal of any kind.
- **FR-026a**: The system MUST NOT reapply the researcher's code when it has not changed, so that
  repeated interactions between edits carry no reload cost and no repeated side effects from
  startup-level code.
- **FR-026b**: Picking up a code change MUST NOT re-run the researcher's startup code. Applying a
  change refreshes handler behavior only. This holds even when the startup code is itself what
  changed.
- **FR-026c**: Changing the startup code takes effect by **starting a fresh session** — either by
  relaunching, or simply by toggling to editor mode and back (FR-015e). This feature MUST NOT provide
  a way to re-run startup within a live session. Re-running setup over a populated
  session risks double-opening connections, double-registering callbacks, and double-appending data;
  a clean slate is what starting up means.
- **FR-026d**: If startup has **never completed successfully** in this session — because the code was
  broken when the interface launched — then it MUST be attempted again on the next interaction, once
  the code loads. This is a deferred first run, not a re-run: nothing has been initialized, so no
  double-initialization is possible. Without it, a researcher who launches with a typo in startup
  would be unable to recover without relaunching, which Principle III forbids.
- **FR-026e**: Once startup has completed successfully, it MUST NOT run again for any reason short of
  a fresh session — that is, a relaunch or a mode switch.

**Surviving faults**

- **FR-027**: A fault in the researcher's code MUST NOT terminate the session under any circumstances.
- **FR-028**: The system MUST distinguish "no handler has been written for this element" from "the
  handler or its file is broken", and MUST NOT treat them alike.
- **FR-029**: An element with no handler MUST do nothing when triggered, without reporting an error.
- **FR-030**: A fault in the researcher's code — whether the file cannot be read as valid code, cannot
  be loaded, or fails while running — MUST be reported to the researcher, identifying what failed and
  where in their code it occurred.
- **FR-031**: After a fault, the researcher MUST be able to correct their code and continue in the same
  session, with all previously held data intact.
- **FR-032**: A fault present when the interface is first launched MUST NOT prevent the interface from
  opening.
- **FR-033**: A fault report MUST appear in two places at once: the full diagnostic detail wherever the
  researcher's textual output goes, and a distinct visual signal in the interface window itself naming
  which element failed and the nature of the failure.
- **FR-033a**: The in-window signal MUST NOT block interaction. The researcher MUST be able to keep
  using every other part of the interface while a fault is displayed, and MUST NOT have to dismiss
  anything before continuing.
- **FR-033b**: The in-window signal MUST clear once the researcher's corrected code runs successfully,
  so that the window always reflects the current state rather than accumulating stale warnings.

**File handling**

- **FR-034**: An interface MUST consist of a layout file and a code file that share a name and location,
  and MUST be addressable by that shared name alone.
- **FR-035**: Both files MUST be located relative to each other, not relative to the directory the
  researcher happened to launch from.
- **FR-036**: A layout file that cannot be understood MUST produce a clear report of what is wrong, and
  MUST NOT be silently discarded or overwritten.
- **FR-036a**: Every layout file MUST record the version of the layout schema that wrote it, from this
  first release onward.
- **FR-036b**: A layout file recording a schema version this build does not recognize — because it was
  written by a newer iterlab — MUST be reported to the researcher as such, naming the situation and
  what to do about it, and MUST NOT be opened, partially interpreted, or written back. Preserving a
  file this version cannot fully understand takes precedence over opening it.
- **FR-036c**: Machinery for migrating layouts between schema versions is **out of scope** for this
  feature. It is written when the first schema-breaking change is actually made, against that real
  change rather than a hypothetical one. This feature's obligation is only to record the version so
  that migration is possible later.

### Key Entities

- **Interface**: A named pairing of one layout and one body of researcher code. The unit a researcher
  creates, edits, and runs. Identified by name alone.
- **Layout**: The set of elements belonging to an interface, each with a type, a unique name, and a
  position and size. Owned by the visual editor; never written by hand as code.
- **Element**: A single visual item — in this feature, a plot area or a button. Has a name that is the
  sole link between the layout and the researcher's code.
- **Handler**: A piece of researcher-written code associated with one element *and one interaction*,
  invoked when that interaction occurs on that element. Every handler is optional. Exactly one — the
  element type's default — is generated empty when the element is created; any others the researcher
  writes themselves. Filled in and owned by the researcher in every case.
- **Session Environment**: The single object passed to every handler, carrying loaded data, computed
  results, and references to every element. Its lifetime is the run of the interface, and it survives
  code changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher who has never used the tool produces a window containing a plot and a working
  button within 2 minutes of starting, having written no layout code.
- **SC-002**: Across a 30-minute algorithm-development session, **100%** of changes to behavior code take
  effect without relaunching, and the number of relaunches caused by code edits is **zero**.
- **SC-003**: A code change is in effect on the next interaction within **2 seconds**, and data loaded
  earlier in the session is **never** reloaded as a consequence of a code change.
- **SC-004**: **100%** of faults in researcher code produce a report that names the fault and its
  location; **0%** end the session.
- **SC-005**: Data and drawings present before a code change are still present after it in **100%** of
  cases.
- **SC-006**: After any sequence of layout edits, the difference in the researcher's code file consists
  only of appended handler stubs — **zero** modifications to existing lines.
- **SC-007**: An interface containing **20 elements** responds to interaction with no delay perceptible
  to the researcher, and adding elements up to that count produces no measurable slowdown in
  responsiveness.
- **SC-008**: For a researcher iterating on an algorithm that requires a slow one-time data load, total
  time spent waiting on reloads across a session is **zero** after the first load.
- **SC-009**: A researcher can recover from a typo and resume work in under **10 seconds**, without
  losing session state.
- **SC-010**: Switching between editor mode and GUI mode takes **one action** and completes in under
  **1 second** for an interface of 20 elements. At no point does switching require leaving the program,
  editing a file, or issuing a command.
- **SC-011**: A researcher can place an element at an exact position by typing coordinates, achieving
  in **one attempt** an alignment that dragging would take several tries to approximate.
- **SC-012**: Renaming an element leaves the code file differing **only** in handler names — zero other
  modified lines, verified by diff.

## Assumptions

**Scope boundaries chosen for this feature**

- Only two element types — plot area and button — are in scope. Text fields, labels, radio buttons,
  checkboxes, dropdowns, lists, and sliders are deliberately deferred, even though the paradigm
  requires them, so that the complete loop can be proven end to end first.
- The universal interaction set (FR-017a) is fixed now because it defines the handler naming
  convention, which later element types must fit into without changing. One convention already
  decided for a deferred type: a **text box** commits its value on Enter or on leaving the field, never
  on every keystroke, so that a handler sees complete input rather than a stream of fragments. It is
  recorded here so the convention is not re-litigated when text boxes are built.
- The properties panel covers position, size, name, and a button's label — all editable, including
  the name. Visual properties such as colors, fonts, borders, and cursors are acknowledged as
  necessary and deferred; each would be a new schema field, and the schema is public surface that is
  expensive to change once shipped.
- Editing convenience features — undo, multi-select, alignment guides, snapping, keyboard nudge,
  duplication, stacking order — are out of scope.
- A single window per interface. Tabs, panels, multiple windows, and detachable plots are out of scope.

**Deliberate trade-offs**

- **Editing and using the interface are two modes of one program**, not two programs. Switching is a
  single click and never involves editing Python or running another command.
- **A mode switch ends the session.** Toggling to the editor discards the running session; toggling
  back starts a fresh one and runs startup again, so loaded data is reloaded. Applying layout edits to
  a *live* session, with data and plots preserved, is the **aim** and is deliberately not promised
  here: it has not been attempted, and per the constitution what avoids a restart is an empirical
  question answered per feature rather than asserted in advance. Recorded as this feature's known
  limit, expected to shrink.
- **Handlers run to completion while the interface waits.** A long computation makes the window
  unresponsive. Keeping the interface live during slow work is a real and important problem, but it is
  deferred rather than solved here.
- Deleting an element leaves its handler behind as dead code. This follows from never destroying
  researcher-written work, and is preferred over the alternative.

**Verification**

- Not everything in a graphical tool can be asserted by a machine. Whether a layout looks right, an
  interaction feels immediate, or a fault banner is actually noticeable requires a person. This feature
  is therefore verified by two gates: automated tests for everything automatable, and a written
  checklist the maintainer works through and records before any release. The manual list holds only
  what genuinely cannot be automated, and is expected to shrink.

**Environment and users**

- A single researcher working alone on their own machine. No collaboration, no multi-user concerns, no
  remote or hosted use.
- Nothing persists between sessions except the two interface files themselves. Window geometry, element
  values, and last-opened state are not remembered.
- The researcher edits their code in whatever editor they already use; the tool provides no editor and
  does not need to know which one is in use.
- The researcher runs the tool in a context where textual output is available to them for full
  diagnostic detail. The interface does not rely on that output being watched, however — per FR-033 the
  window itself signals faults independently, so a researcher looking only at their plots still learns
  that something broke.
- Interfaces are not packaged or distributed to colleagues in this feature.

**Fixed by the project constitution, not decided here**

- The layout file format, the graphical toolkit, and the plotting mechanism are already settled as
  project-wide constraints and are not open questions for this specification. They are recorded in
  `.specify/memory/constitution.md` and applied at planning time.
- The requirement never to crash on researcher code, and the requirement that code changes take effect
  without restarting, are non-negotiable project principles. This feature is their first implementation,
  not a place where they are traded away.
