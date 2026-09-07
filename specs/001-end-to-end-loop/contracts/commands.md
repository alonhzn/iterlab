# Contract: Commands And Entry Points

**Public surface item 5** — the commands to edit and run an interface, and the file-pairing convention
they rely on. MAJOR-only.

---

## Two commands, nothing else

```console
iterlab edit <name>     # open the designer canvas
iterlab run  <name>     # run the interface
```

Principle I requires exactly this: one command to edit, one to run, no scaffolding step, no
registration, no configuration beyond the name.

The equivalent library calls, for researchers who prefer to launch from a script or an IDE:

```python
from iterlab import edit, run

edit("demo")
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

## `iterlab edit <name>`

| Situation | Behavior |
|---|---|
| Neither file exists | Create both — an empty layout and the starter code file — then open the canvas (FR-002) |
| Layout exists, code file does not | Create the starter code file, then open |
| Code file exists, layout does not | Create an empty layout, then open. Existing code is **never** touched |
| Both exist | Open, showing existing elements at their saved positions |
| Layout has a newer `schema_version` | Report and exit non-zero. Do not open, do not modify |
| Layout is invalid | Report what is wrong and exit non-zero. Do not overwrite |

In the canvas: drag to create; name the element when it is created, with a default pre-filled;
click to select; drag or resize a selection; delete a selection. Layout changes save automatically
(FR-008). Creating an element appends its stub (FR-009). Deleting one leaves its handler in place
(FR-012).

Renaming is **not offered**, because it is out of scope this feature and Principle I's promise is
undermined by offering an action that cannot be honored (FR-005c).

## `iterlab run <name>`

| Situation | Behavior |
|---|---|
| Both files exist and are valid | Open the window, run `on_startup`, accept interaction |
| Code file will not load | **Open anyway**, report the fault, remain usable (FR-032) |
| Layout is missing | Report; suggest `iterlab edit <name>`; exit non-zero |
| Layout has a newer `schema_version` | Report and exit non-zero |
| Layout has no elements | Open an empty window without complaint |

The asymmetry is deliberate and constitutional: a broken **layout** is a stop, because guessing at it
risks destroying it. Broken **researcher code** is never a stop, because stopping is exactly the cost
Principle III exists to eliminate.

### In the running window

| Affordance | Purpose |
|---|---|
| Plot toolbar | Pan and zoom, with no handler written (FR-017e) |
| Fault banner | Non-blocking; names the failed element and the failure; clears when corrected code runs (FR-033a, FR-033b) |

These are application chrome, not layout. They are not elements, do not appear in the layout file, and
cannot be moved or deleted by the researcher.

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Window opened and closed normally. **A fault in researcher code does not change this** — surviving faults is correct behavior, not failure |
| `1` | Could not start: layout invalid, newer schema version, or missing file for `run` |
| `2` | Usage error: no name given, unreadable path |
| `3` | `tkinter` unavailable — message names the component and the install command (R12) |

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

Additive and therefore **MINOR**: a new command; a new optional flag; a new accepted name form; a new
window affordance.

Breaking and therefore **MAJOR**: renaming or removing a command; changing name resolution; changing
the `<name>.yaml` / `<name>.py` pairing; making a currently-optional argument required; changing an
exit code's meaning; making a researcher-code fault non-zero.
