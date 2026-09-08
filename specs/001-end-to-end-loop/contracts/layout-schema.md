# Contract: Layout File Schema

**Public surface item 1.** Under the constitution's *Release And Versioning*, a breaking change here
requires a MAJOR release. A layout written by any version MUST open in every later version.

**Schema version**: `2` | **Format**: YAML | **Filename**: `<interface-name>.yaml`

---

## Amendments since this contract was written

The shape below is the schema as first specified, at version 1. Two changes have
landed since, each with a migration in `layout/store.py` and a test that opens a
file written by the older build:

| Version | Change |
|---|---|
| 2 | Added the per-element `style` block. An absent block means every default, which is what a v1 element had. |
| 3 | Renamed the element type `plot_area` to `axes`, and the suggested tag prefix from `plot` to `ax`. Tags, positions and styles are untouched, so names chosen before the rename survive it. |

The current `SCHEMA_VERSION` is **3**. Everything else below still holds; the
element type names in the examples are shown as they are written today.

## Shape

```yaml
schema_version: 1

window:
  width: 800
  height: 450

elements:
  ax_0:
    type: axes
    position: [0.05, 0.30, 0.90, 0.65]

  run_fit:
    type: button
    position: [0.05, 0.10, 0.20, 0.10]
    label: Run fit
```

A minimal valid layout — a new interface before anything is drawn:

```yaml
schema_version: 1
window:
  width: 800
  height: 450
elements: {}
```

---

## Field contract

| Path | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `schema_version` | int | **yes** | — | Written as `1`. See *Version gate*. |
| `window.width` | int | no | `800` | > 0 |
| `window.height` | int | no | `450` | > 0 |
| `elements` | map | **yes** | `{}` | Keys are element tags |
| `elements.<tag>.type` | str | **yes** | — | `axes` \| `button` |
| `elements.<tag>.position` | list[float] × 4 | **yes** | — | `[left, bottom, width, height]`, each in `[0,1]`; `left+width ≤ 1`; `bottom+height ≤ 1` |
| `elements.<tag>.label` | str | no | `""` | text-bearing types only (`button`, `label`) |
| `elements.<tag>.style` | map | no | `{}` | appearance; only non-defaults are written |

### `style`

Which properties an element has depends on its type. A `axes` takes only
`visible`; matplotlib owns the rest of how a plot looks.

| Key | Type | Default | Applies to |
|---|---|---|---|
| `background` | colour | theme | button, label |
| `text_color` | colour | theme | button, label |
| `edge` | colour | theme | button, label |
| `edge_width` | int ≥ 0 | `0` | button, label |
| `font` | family name | theme | button, label |
| `font_size` | 1–200 | theme | button, label |
| `bold` | bool | `false` | button, label |
| `italic` | bool | `false` | button, label |
| `align` | `left`/`center`/`right` | `center` | button, label |
| `enabled` | bool | `true` | button, label |
| `visible` | bool | `true` | every type |

A colour is `#rgb`, `#rrggbb`, or a Tk colour name. A style key a type does not
have is a validation error, not something ignored.

**These are starting values.** Researcher code may change any of them at run
time; doing so alters the live widget and never writes back to this file.

**Element tag** (the map key) MUST satisfy all of: `str.isidentifier()`; not a Python keyword; does
not begin with `_`; unique within the file. The name becomes part of a function name and an attribute,
so an invalid name would produce uncompilable generated code.

**Position origin** is bottom-left, matching matplotlib. Values are written rounded to 4 decimals.

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
| Lower | Migrate, tell the researcher it happened, then open. **No migration exists in this release** — version 1 is the first, so this case is unreachable and MUST raise an internal error rather than be silently tolerated |
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

---

## Compatibility rules for future versions

Additive and therefore **MINOR**: a new element type; a new optional per-element property with a
default; a new optional `window` key.

Breaking and therefore **MAJOR**: renaming or removing any field; changing `position` semantics or
ordering; changing the coordinate origin; making an optional field required; changing name validity
rules to reject names that were previously legal.

Per-type properties live under the element rather than in a shared namespace precisely so that adding
one to `button` cannot affect `axes`.
