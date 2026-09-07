# Contract: Command And Modes

**Public surface item 5** — the command that opens an interface, the two modes it presents, and the
file-pairing convention it relies on. MAJOR-only.

---

## One command

```console
iterlab <name>
```

That is the whole command surface. There is no separate command for editing and using an interface:
Principle I requires that they be two modes of one program, switched from inside the interface.

The library equivalent, for researchers who prefer to launch from a script or an IDE:

```python
from iterlab import run

run("demo")
```

Both forms are the same public surface. Neither offers any way to construct a layout in code — that
would violate Principle I, so no such API exists.

---

## Name resolution

`<name>` may be a bare name or a path.

| Given | Layout | Code |
|---|---|---|
| `demo` | `./demo.yaml` | `./demo.py` |
| `work/demo` | `work/demo.yaml` | `work/demo.py` |
| `/abs/path/demo` | `/abs/path/demo.yaml` | `/abs/path/demo.py` |
| `demo.yaml` or `demo.py` | `demo.yaml` | `demo.py` — the extension is stripped, so either file can be named |

**Everything resolves relative to the pair's own directory, never to the working directory** (FR-035).
A relative `<name>` is resolved against the working directory *once*, to locate the pair; from then on
the pair's directory is the reference. Launching from elsewhere must not break an interface.

Accepting `demo.yaml` and `demo.py` interchangeably matters in practice — a researcher with the file
open in an editor will tab-complete one of them.

---

## Opening an interface

| Situation | Behavior |
|---|---|
| Neither file exists | Create both — an empty layout and the starter code file — then open in **editor mode** (FR-002) |
| Layout exists, code file does not | Create the starter code file, then open |
| Code file exists, layout does not | Create an empty layout, then open. Existing code is **never** touched |
| Layout has no elements | Open in **editor mode** — there is nothing to use yet (FR-001a) |
| Layout has elements | Open in **GUI mode** — ready to use (FR-001a) |
| Code file will not load | **Open anyway**, report the fault, remain usable (FR-032) |
| Layout has a newer `schema_version` | Report and exit non-zero. Do not open, do not modify |
| Layout is invalid | Report what is wrong and exit non-zero. Do not overwrite |

The asymmetry in the last three rows is deliberate and constitutional. A broken **layout** is a stop,
because guessing at it risks destroying it. Broken **researcher code** is never a stop, because
stopping is exactly the cost Principle III exists to eliminate.

Start mode is chosen by whether elements exist rather than by a flag, so a new interface lands where
the researcher has to begin anyway, and an existing one lands ready to use. Neither case requires a
decision before the window opens.

---

## The two modes

### Editor mode

| Region | Contents |
|---|---|
| Canvas | The layout being drawn. Drag to create, click to select, drag or resize a selection, delete a selection |
| Palette | Every element type that can be added, so the vocabulary is discoverable without documentation (FR-003a) |
| Properties panel | The selected element's properties, all editable (FR-006a–e) |

Properties exposed per type:

| Type | Properties |
|---|---|
| `button` | position, name, label |
| `plot_area` | position, name |

Every one is editable, **including the name** — renaming rewrites that element's handlers in the code
file and changes nothing else (FR-005c, FR-005d). Position is editable both by dragging and by typing
values, and the two must produce identical results (FR-006c).

Layout changes save automatically; the researcher never issues a save (FR-008). Creating an element
appends its stub (FR-009). Deleting one leaves its handler in place (FR-012).

### GUI mode

The interface as drawn: elements at their positions, handlers wired, startup run. Plot areas carry the
standard plotting toolbar with no handler written (FR-017e). Faults appear in a non-blocking banner
(FR-033).

---

## The mode toggle

A control in the **top-left corner**, present and operable in both modes (FR-015, FR-015a).

| Property | Contract |
|---|---|
| Always visible | Rendered above every element; never obscured by anything drawn (FR-015b) |
| Footprint shown | Editor mode indicates the area it occupies, so a researcher can choose not to put something important beneath it |
| Not layout | Never appears in the layout file, cannot be moved or deleted, is not reachable from researcher code (FR-015c) |

### What a mode switch does to the session

| Direction | Effect |
|---|---|
| GUI → editor | **The session ends.** `ev` is discarded along with loaded data and drawn plots |
| editor → GUI | **A fresh session begins.** A new `ev` is created and `on_startup` runs |

This is the feature's known limit, recorded rather than hidden. Applying layout edits to a *live*
session with data and plots preserved is the aim; it has not been attempted, so it is not promised
(constitution Principle IV, and spec Assumptions).

One useful consequence: because a switch begins a fresh session, **toggling out and back applies a
change to the startup code** without leaving the program (FR-015e, FR-026c). There is still no way to
re-run startup *within* a live session, so the double-initialization hazard does not return.

---

## Chrome is not layout

The toggle, the palette, and the properties panel are application chrome. They are not elements, do
not appear in the layout file, cannot be moved or deleted by the researcher, and are not reachable
from researcher code. A researcher's `ev` contains exactly the elements they drew and nothing else.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | The window opened and closed normally. **A fault in researcher code does not change this** — surviving faults is correct behavior, not failure |
| `1` | Could not start: layout invalid, or a newer schema version |
| `2` | Usage error: no name given, unreadable path |
| `3` | `tkinter` unavailable — the message names the component and the install command (R12) |

`tkinter` gets its own code because it is the one predictable environment failure, and a Linux
researcher hitting a bare `ModuleNotFoundError` has no way to know what to do.

---

## Streams

- **stdout**: whatever the researcher's own code prints. iterlab does not compete for it.
- **stderr**: iterlab diagnostics and full fault tracebacks (FR-033's detail channel).

Keeping the researcher's `print()` output uncontaminated matters — printing values is half of how
algorithm development actually gets done.

---

## Compatibility rules

Additive and therefore **MINOR**: an optional flag, such as one forcing a start mode; a new element
type in the palette; a new property in the panel; a new window affordance; a new accepted name form.

Breaking and therefore **MAJOR**: renaming or removing the command; reintroducing a mode-specific
command; changing name resolution; changing the `<name>.yaml` / `<name>.py` pairing; making a
currently-optional argument required; changing an exit code's meaning; making a researcher-code fault
non-zero; removing the toggle or making a mode switch require anything beyond a single action.
