# Phase 1 Data Model: End-to-End Minimal Loop

**Feature**: 001-end-to-end-loop | **Date**: 2026-09-07

Entities are grouped by lifetime, because lifetime is the load-bearing property in this design: what
survives a reload is exactly what Principle IV protects.

| Group | Lifetime | Survives reload? |
|---|---|---|
| Persistent | On disk between sessions | Not applicable |
| Session | From launch to window close | **Yes — this is the point** |
| Transient | One interaction | No |

---

## Persistent entities

### Interface

The unit a researcher creates, edits, and runs. Not a stored object — an addressing convention.

| Field | Type | Rules |
|---|---|---|
| `name` | str | The shared basename of the pair. Supplied by the researcher on the command line. |
| `directory` | path | Directory containing both files. All resolution is relative to this, never to the working directory (FR-035). |

Derived: `layout_path = directory/f"{name}.yaml"`, `code_path = directory/f"{name}.py"`.

**Lifecycle**: opening a name that does not exist creates both files — an empty layout and a starter
code file (FR-002). There is no other creation path and no separate initialization step.

---

### Layout

The complete visual definition of one interface. Owned exclusively by `layout/`; the code generator
never reads or writes it.

| Field | Type | Default | Rules |
|---|---|---|---|
| `schema_version` | int | `1` | Written on every save (FR-036a). Higher than current → report and refuse to open (FR-036b). |
| `window` | Window | see below | Exactly one. |
| `elements` | ordered map of name → Element | `{}` | Keys are element names; uniqueness is structural (FR-005). Order is preserved for stable diffs. |

**Validation**: every element name valid per *Element.name*; no element extends outside `[0, 1]`;
`schema_version` present and an integer.

---

### Window

| Field | Type | Default | Rules |
|---|---|---|---|
| `width` | int | `800` | Initial width in pixels. Advisory — the window is resizable. |
| `height` | int | `450` | Initial height in pixels. |

Stored in pixels rather than fractions because it is the reference the fractions are *of*. Constitution
Principle I anticipates canvas size becoming a pre-configuration later; the default must work unasked.

---

### Element

One visual item. The name is the sole link to the researcher's code (Principle II).

| Field | Type | Default | Rules |
|---|---|---|---|
| `name` | str | assigned | Unique within the layout. MUST satisfy `isidentifier()`, MUST NOT be a Python keyword, MUST NOT start with `_` (R10, FR-005b). Set at creation and **changeable** through the properties panel; renaming rewrites the element's handlers in the code file and nothing else (FR-005c, FR-005d, R14). |
| `type` | enum | — | `axes` \| `button`. Closed set this feature. |
| `position` | Rect | — | Normalized `[0, 1]` fractions (Principle II, FR-021a). |
| `label` | str | `""` | Buttons only. Display text; never affects the name or any handler. |

**Default name generation**: `f"{type_prefix}_{n}"` with the lowest `n` not in use — `button_0`,
`plot_0`. Pre-filled in the creation dialog so it can be accepted without typing (FR-005a).

**Extensibility**: per-type properties live in a nested block so that adding a property to one type is
an additive schema change (Principle II, FR-036c, and the constitution's MINOR rule). `label` is the
first such property.

### Rect

| Field | Type | Rules |
|---|---|---|
| `left`, `bottom`, `width`, `height` | float | Each in `[0, 1]`; `left + width <= 1`; `bottom + height <= 1`. Rounded to 4 decimal places on save for readable diffs. |

Origin is bottom-left, matching matplotlib's convention and the prior spike's stored layouts.

---

## Session entities

### Ev — the session environment

Constructed by the runtime at launch, passed as the first argument to every handler, and **owned by
the runtime, never by the researcher's module** (R1). This ownership is the mechanism by which
Principle IV's "reload discards nothing" is achieved.

| Attribute | Type | Purpose |
|---|---|---|
| `<element_name>` | widget handle | One attribute per element, named exactly as in the designer (FR-019). |
| *researcher's own* | anything | Whatever the researcher assigns — loaded data, computed results, cached models. Never touched by iterlab. |

**Reserved**: attribute names beginning with `_` are iterlab's. This is why element names may not start
with an underscore (R10).

**Lifetime**: created when GUI mode begins; destroyed when GUI mode ends — that is, on window close
**or on a switch to editor mode** (FR-015d). Explicitly **survives** every code reload and every fault
within a session. A fresh `ev` and a fresh run of startup are what a mode switch back to GUI mode
produces, which is also the only way to re-run startup (FR-026c, R13).

**Collision rule**: an element name that would shadow an attribute the researcher already set is a
name conflict, resolved in favor of the element, since names are validated as unique at creation.

---

### Mode

Which of the two faces of the program is currently built. Owned by `ui/app.py`, one per process.

| Value | What exists |
|---|---|
| `editor` | Canvas, palette, properties panel. No `ev`, no running session |
| `gui` | The realized layout, a live `ev`, handlers wired |

**State transitions**:

```text
   (open, no elements) → EDITOR ⇄ GUI ← (open, has elements)
                            │       │
                            │       └─ toggle: destroy ev, tear down widgets
                            └───────── toggle: build widgets, new ev, run startup
```

Both transitions destroy every content widget and build the other mode's. The Tk root, the window
geometry, and the mode toggle persist across both (R13). Nothing else does — which is precisely why a
session does not survive a switch.

### Selection

Editor mode only. Which element the properties panel is describing.

| Field | Type | Rules |
|---|---|---|
| `element_name` | str or `None` | `None` means nothing selected, and the panel MUST say so rather than showing a blank form (FR-006a) |

Transient: discarded on every mode switch, and never written to the layout file.

### LoadedModule

The runtime's record of the researcher's code file. One per session.

| Field | Type | Purpose |
|---|---|---|
| `module` | module or `None` | `None` while the file does not load. |
| `stamp` | (int, int) | `(st_mtime_ns, st_size)` at last successful load. The change check (R2). |
| `load_fault` | Fault or `None` | Why the last load attempt failed, if it did. |

**State transitions**:

```text
                  ┌────────────────────────────────┐
                  │                                │
    (launch) → UNLOADED ─load ok→ CURRENT ─stamp changed→ STALE
                  │                 │                        │
                  └─load fails→ BROKEN ←─────load fails──────┘
                                    │                        │
                                    └──────load ok───────────┘ → CURRENT
```

- **BROKEN is not terminal.** Every subsequent interaction retries the load, which is what lets a
  researcher fix a syntax error and carry on in the same session (FR-031).
- Entering BROKEN does **not** discard the previously loaded module reference, but handlers are not
  served from it — serving stale code silently would be worse than doing nothing and reporting.

---

### Element handle

The live widget for one element, reachable as `ev.<name>`.

| Element type | Exposed to the researcher |
|---|---|
| `axes` | The matplotlib `Axes`. Researchers call `ev.plot_0.plot(...)` — the API they already know. |
| `button` | A handle exposing its label; deliberately minimal this feature. |

The `Axes` choice matters: exposing anything else would mean researchers learning an iterlab plotting
API, which the constitution's rationale for matplotlib explicitly rejects.

---

## Transient entities

### Event

Normalized across Tk and matplotlib so that handler signatures do not depend on element type (R9).

| Field | Type | Present when |
|---|---|---|
| `kind` | enum | Always. `click` \| `hover` \| `move` \| `key`. |
| `element` | str | Always. Name of the element. |
| `button` | enum or `None` | Click events — `left` \| `middle` \| `right` (FR-017c). |
| `x`, `y` | float or `None` | **Data coordinates** for plot areas; `None` for controls. |
| `key` | str or `None` | Key events. |
| `double` | bool | Click events. |

`x`/`y` being data coordinates rather than pixels is the whole reason plot events come from matplotlib
rather than Tk.

### Fault

| Field | Type | Purpose |
|---|---|---|
| `kind` | enum | `load_failed` \| `handler_raised`. Never used for "no handler written" — that is not a fault (FR-029). |
| `element`, `interaction` | str or `None` | `None` for load failures, which are not attributable to one element. |
| `message` | str | One line, for the in-window banner. |
| `traceback_text` | str | Full detail, for the console channel. |

The absence of a "no handler" fault kind is deliberate and structural: it makes conflating the two
cases (the prior spike's defect) impossible to express in the type system.

---

## Entity relationships

```text
Interface ─1:1─ Layout ──1:N── Element
    │              │
    │              └─1:1── Window
    │
    └─1:1─ code file ──N handlers, 0..1 generated per element

  ── at run time ──

Ev ──1:N── Element handle          (ev.<name>)
 │
 └─ holds researcher state ────────  survives reload  ← Principle IV

LoadedModule ──serves──> handler functions ──resolved by name at each invocation
                                              never stored  ← R2

Event ──> dispatch ──> handler ──raises──> Fault ──> FaultSink (console + banner)
```
