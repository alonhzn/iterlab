# Contract: Layout File Schema

**Public surface item 1.** Under the constitution's *Release And Versioning*, a breaking change here
requires a MAJOR release. A layout written by any version from 2.0.0 onward MUST open in every later
version.

**Schema version**: `8` | **Format**: a Python module holding one literal | **Filename**:
`<interface-name>_layout.py`

---

## History

Schemas 1 to 7 were YAML, in `<interface-name>.yaml`, each moving forward with a migration and a test.
2.0.0 replaced the format with a Python module and deliberately shipped **no** migration: iterlab had
no users at the time, so nobody had a layout to lose. That exception is recorded in the constitution,
dated, and does not extend to any later release. Schema 8 is the first version of this format, and
the migration table in `layout/store.py` is empty for that reason, not by omission.

A `.yaml` layout from 1.x is not read. Opening its folder prints a notice naming the file, says the
file was not touched, and opens a new interface beside it.

---

## Shape

The file holds what was drawn, and the class an editor reads to complete `ev.` inside a handler. One
write produces both, so they cannot drift apart:

```python
"""Written by iterlab. Rewritten whenever you change the interface."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from iterlab.types import Axes, Button

LAYOUT = {
    'schema_version': 8,
    'iterlab_version': '2.1.0',
    'window': {'width': 960, 'height': 492},
    'toolbar_collapsed': False,
    'elements': {
        'ax_0': {'type': 'axes', 'position': [0.05, 0.3, 0.9, 0.65]},
        'run_fit': {'type': 'button', 'position': [0.05, 0.1, 0.2, 0.1], 'label': 'Run fit'},
    },
}


class Ev:
    """Your interface, as your editor sees it."""

    ax_0: "Axes"
    run_fit: "Button"
```

A minimal valid file — the least iterlab will accept — is a single assignment:

```python
LAYOUT = {'schema_version': 8, 'elements': {}}
```

---

## Read, never run

**iterlab never imports this file.** It is parsed, the `LAYOUT` assignment is found in the parse
tree, and its value is evaluated as literals only. Nothing else in the file executes on load.

This is the guarantee the format rests on. A layout is something people send each other, and
importing one would make every shared interface arbitrary code execution on open.

The consequence is deliberate: every value in `LAYOUT` has to be written out. A computed value such
as `os.getpid()` is refused as an invalid layout rather than evaluated. The `Ev` class and its
import sit under `TYPE_CHECKING` and exist only for editors.

---

## Field contract

| Path | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `schema_version` | int | **yes** | — | Written as `8`. See *Version gate* |
| `iterlab_version` | str | no | — | The iterlab that last wrote the file. Always rewritten on save |
| `window.width` | int | no | half the screen when created | > 0; the interface area, not the whole window |
| `window.height` | int | no | half the screen less the top bar | > 0 |
| `toolbar_collapsed` | bool | no | `False` | Whether the editor's toolbar is folded |
| `elements` | map | **yes** | `{}` | Keys are element tags |
| `elements.<tag>.type` | str | **yes** | — | `axes`, `button`, `label`, `text_box`, `number_box`, `file_select`, `folder_select` |
| `elements.<tag>.position` | list[float] × 4 | **yes** | — | `[left, bottom, width, height]`, each in `[0,1]`; `left+width ≤ 1`; `bottom+height ≤ 1` |
| `elements.<tag>.label` | str | no | `""` | Text-bearing types only: everything except `axes` |
| `elements.<tag>.extensions` | str | no | `""` | `file_select` only. Comma-separated, e.g. `"csv, txt"`; empty means every file |
| `elements.<tag>.style` | map | no | `{}` | Appearance; only non-defaults are written |

### `style`

Which properties an element has depends on its type. An `axes` takes only `visible`; matplotlib owns
the rest of how a plot looks.

| Key | Type | Default | Applies to |
|---|---|---|---|
| `background` | colour | theme | every text-bearing type |
| `text_color` | colour | theme | every text-bearing type |
| `edge` | colour | theme | every text-bearing type |
| `edge_width` | int ≥ 0 | `0` | every text-bearing type |
| `font` | family name | theme | every text-bearing type |
| `font_size` | 1–200 | theme | every text-bearing type |
| `bold` | bool | `False` | every text-bearing type |
| `italic` | bool | `False` | every text-bearing type |
| `align` | `left`/`center`/`right` | `center` | every text-bearing type |
| `enabled` | bool | `True` | every text-bearing type |
| `visible` | bool | `True` | every type |

A colour is `#rgb`, `#rrggbb`, or a Tk colour name. A style key a type does not have is a validation
error, not something ignored.

**These are starting values.** Researcher code may change any of them at run time; doing so alters the
live widget and never writes back to this file.

**Element tag** (the map key) MUST satisfy all of: `str.isidentifier()`; not a Python keyword; does
not begin with `_`; unique within the file. The name becomes part of a function name and an attribute,
so an invalid name would produce uncompilable generated code.

**Position origin** is bottom-left, matching matplotlib. Values are held to two decimals — hundredths
of the window — in the editor and in the file alike.

**Unknown keys** within a recognized `schema_version` are a validation error, not silently ignored —
silently dropping them would delete them on the next save.

**Chrome is never in the layout.** The mode toggle, the palette, and the properties panel are
application furniture, not elements. They never appear in this file, and a layout file therefore
describes exactly what the researcher drew (FR-015c).

---

## Version gate

| File's `schema_version` | Behavior |
|---|---|
| Equal to this build's | Open normally |
| Lower | Migrate, tell the researcher it happened, then open. No migration exists yet: schema 8 is the first of this format, so a lower version cannot occur in a file of this shape |
| Higher | **Report and stop.** Do not open, do not partially interpret, do not write back |
| Missing or not an integer | Report as an invalid layout file |

Refusing a higher version is the important case. Opening it, dropping the properties this build does
not understand, and saving it back would silently destroy work — the data loss Principle V exists to
prevent. Preserving a file this build cannot fully understand takes precedence over opening it.

---

## Write guarantees

- Writes are atomic: a temporary file in the same directory, then `os.replace()`.
- `elements` order is preserved across a load/save round trip, so version-control diffs stay small.
- Saving is automatic on layout change; the researcher never issues a save (FR-008).
- A load/save round trip with no edits MUST produce a byte-identical file. This is a contract test.
- The file is formatted for a person to read: one thing per line, four-space indents, and anything
  that fits left on one line.

---

## Compatibility rules for future versions

Additive and therefore **MINOR**: a new element type; a new optional per-element property with a
default; a new optional `window` key.

Breaking and therefore **MAJOR**: renaming or removing any field; changing `position` semantics or
ordering; changing the coordinate origin; making an optional field required; changing name validity
rules to reject names that were previously legal; changing the file's format or name. Each needs a
migration, as the constitution requires.

Per-type properties live under the element rather than in a shared namespace precisely so that adding
one to `button` cannot affect `axes`.
