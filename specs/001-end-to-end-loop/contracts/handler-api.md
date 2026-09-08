# Contract: Handler API

**Public surface items 2, 3, and 4** — the naming convention, the handler contract, and the generated
stub shape. This is the contract consumed *directly by researcher-written code*, so breaking it breaks
existing analyses rather than an integration. MAJOR-only.

---

## Naming convention

```text
on_<interaction>_<tag>
```

| Interaction | Function name | Fires when |
|---|---|---|
| `clicked` | `on_clicked_<tag>` | A mouse button is pressed on the element |
| `hover` | `on_hover_<tag>` | The pointer enters the element |
| `motion` | `on_motion_<tag>` | The pointer moves within the element |
| `key` | `on_key_<tag>` | A key is pressed while the element has focus |

**Universal**: every interaction is available on every element type (FR-017a). A hover handler on a
button is as legitimate as one on a plot area.

**Optional**: a handler exists only if the researcher wrote it. A missing handler is a silent no-op and
is never an error (FR-017b, FR-029).

**Startup**: `on_startup(ev)` runs once at launch, before any interaction is possible. It is never
re-run implicitly, including when it is itself what changed (FR-026b). Changing it takes effect by
starting a fresh session — which the mode toggle provides in one click — and there is no in-session
re-run (FR-026c, FR-015e). The sole exception is a startup that never completed successfully, which is
attempted again once the code loads (FR-026d).

---

## Signature

```python
def on_clicked_run_fit(ev, event):
    ...
```

| Parameter | What it is |
|---|---|
| `ev` | The session environment. Same object for the entire session; survives every reload. |
| `event` | What just happened. A fresh object per interaction. |

Both are positional. Names are conventional, not enforced — iterlab passes positionally, so a
researcher may rename them, though every generated stub uses `ev` and `event`.

`on_startup` takes `ev` only.

**Return value is ignored.** Handlers act through `ev` and through the plotting API.

---

## `ev` — the session environment

```python
def on_startup(ev):
    ev.data = np.loadtxt("measurements.csv")   # loaded ONCE per session
    ev.plot_0.plot(ev.data)

def on_clicked_run_fit(ev, event):
    ev.result = fit(ev.data)                   # ev.data still here, not reloaded
    ev.plot_0.plot(ev.result)
```

| Access | Meaning |
|---|---|
| `ev.<tag>` | The live handle for that element, named exactly as in the designer |
| `ev.<anything_else>` | Yours. Assign freely; iterlab never reads or modifies it |
| `ev._<anything>` | **Reserved for iterlab.** This is why element tags may not begin with `_` |

**The guarantee that matters**: `ev` is created by iterlab, not by the researcher's module, and
therefore survives every reload of that module. Data loaded in `on_startup` is loaded once per session
however many times the code is edited.

**Element handles**:

| Type | Handle |
|---|---|
| `plot_area` | A matplotlib `Axes`. Use the matplotlib API you already know. |
| `button` | A handle exposing its label. Deliberately minimal this feature. |

---

## `event`

Normalized across element types, so a handler signature never depends on how an element is implemented.

| Attribute | Type | Present when |
|---|---|---|
| `kind` | str | Always — `"click"`, `"hover"`, `"motion"`, `"key"` |
| `tag` | str | Always — the element's tag |
| `button` | str or `None` | Click — `"left"`, `"middle"`, `"right"` |
| `x`, `y` | float or `None` | **Data coordinates** on plot areas; `None` on controls |
| `key` | str or `None` | Key events |
| `double` | bool | Click — whether it was a double click |

`x` and `y` are in the plot's own data coordinates, not pixels. Clicking a spectrum at 512 nm gives you
`512.0`, not a screen offset. This is the reason plot events come from matplotlib rather than Tk.

---

## Generated stub shape

Creating an element appends **exactly one** stub — that element type's default interaction (FR-017d).
Stubs for other interactions are never generated; the researcher writes those when wanted.

| Element type | Default interaction | Generated |
|---|---|---|
| `plot_area` | click | `on_clicked_<tag>` |
| `button` | click | `on_clicked_<tag>` |

```python
def on_clicked_run_fit(ev, event):
    # Runs when you click run_fit.
    # Delete this function if you don't need it — nothing will break.
    print(f"run_fit clicked with the {event.button} button")
```

**Contract on generated code:**

- Appended at end of file, after a blank-line separator.
- Appended **only** if no top-level function of that name already exists, determined by parsing the
  file — so reformatting, comments, and decorators cannot cause a duplicate.
- Nothing else in the file is read back, rewritten, reordered, or removed (Principle V).
- If the file does not currently parse, the append is refused and reported, rather than risking a
  duplicate definition.
- Written atomically: temporary file in the same directory, then `os.replace()`.

The signature is public surface; the comment text is not, and may be reworded in a PATCH.

---

## The starter code file

Created alongside a new layout when an interface is opened for the first time (FR-002):

```python
"""<name> — an iterlab interface.

Open it:  iterlab <name>
Switch between editing and using it with the toggle in the top-left corner.
"""


def on_startup(ev):
    # Runs once when the interface opens, before anything else.
    #
    # Load your data HERE, not at the top of this file. Anything at module level
    # re-runs when iterlab picks up an edit; anything in here does not.
    pass
```

The comment about module-level code is deliberate, and is the mitigation for the one accepted
limitation in this design (research.md R3): reloading a module necessarily re-executes its top level,
so a researcher who loads data there will see it reload. Making the safe path the obvious one is the
only available defense.

---

## Renaming an element

Renaming an element in the properties panel rewrites **that element's handlers** in the code file, and
nothing else (FR-005c, FR-005d).

```python
# before — element tagd axes_0
def on_clicked_axes_0(ev, event): ...
def on_motion_axes_0(ev, event): ...

# after — renamed to spectrum
def on_clicked_spectrum(ev, event): ...
def on_motion_spectrum(ev, event): ...
```

**Contract on renaming:**

- Every handler for that element is renamed together; handlers for other elements are untouched, even
  if their names contain the old name as a substring.
- Only the identifiers in the function definitions change. Comments, string literals, local variables,
  formatting, and ordering are preserved byte for byte — the rewrite is driven by AST node positions,
  never by text substitution (R14).
- A rename is refused, with nothing modified, if the new name is unusable in code or already taken
  (FR-005e), or if the code file does not currently parse (FR-005f).
- The code file is rewritten before the layout file, so a failure leaves the two consistent.
- The write is atomic.

This is the **only** operation in iterlab permitted to modify a line the researcher wrote.

---

## Compatibility rules

Additive and therefore **MINOR**: a new interaction kind; a new attribute on `event`; a new element
type; a new element handle capability.

Breaking and therefore **MAJOR**: changing the `on_<interaction>_<tag>` pattern; changing parameter
order or count; renaming an `event` attribute; changing `x`/`y` away from data coordinates; changing
what `ev.<tag>` returns; making `ev` not survive a reload; generating more than one stub per
element.
