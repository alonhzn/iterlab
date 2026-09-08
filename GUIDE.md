# iterlab user guide

The GUI as a place to *develop* an algorithm, not a wrapper you bolt on afterwards.

You draw the interface. You write the algorithm. iterlab keeps the two in separate files and gets
out of the way — including staying alive while you edit, so you stop paying to restart.

> This guide grows with the tool. It documents what works **today**, in the version named at the
> bottom. If something here does not behave as described, that is a bug — please say so.

---

## Install

iterlab is not on PyPI yet, so install from the repository:

```console
git clone https://github.com/alonhzn/iterlab.git
cd iterlab
pip install -e .
```

**On Linux** you also need tkinter, which is packaged separately and cannot come from PyPI:

```console
sudo apt install python3-tk        # Debian, Ubuntu
sudo dnf install python3-tkinter   # Fedora, RHEL
```

It ships with Python on Windows and macOS. If it is missing, iterlab exits with code 3 and tells
you which package to install rather than an unexplained `ImportError`.

---

## Your first interface

```console
iterlab demo
```

One command. That is the whole command surface — there is no separate "edit" and "run".

Because `demo` does not exist yet, iterlab creates two files beside each other and opens the
**editor**:

```
demo.yaml    the layout - iterlab owns this, you never hand-edit it
demo.py      your code - you own this, iterlab only ever appends to it
```

### Draw something

1. Pick a type from **ADD ELEMENT** on the left.
2. **Drag** on the canvas to size it, or **click** to drop one at a sensible default size.
3. The **PROPERTIES** panel opens with the tag pre-filled. Type over it if you want a better one.

Draw a **Plot area** tagged `spectrum` and a **Button** tagged `run_fit`.

`demo.py` now ends with one handler for each. iterlab appends; it never edits or removes anything
you wrote.

### Write the algorithm

Open `demo.py` in your own editor:

```python
import numpy as np


def on_startup(ev):
    # Runs once when the interface opens. Load your data HERE, not at the top
    # of the file - see "The one gotcha" below.
    ev.x = np.linspace(0, 10, 500)
    ev.spectrum.plot(ev.x, np.sin(ev.x))


def on_clicked_run_fit(ev, event):
    ev.spectrum.clear()
    ev.spectrum.plot(ev.x, np.sin(2 * ev.x))
```

### Use it

Click **Run it** in the top-left corner. The window becomes your interface. Click the button and
your code runs.

Click **Edit layout** to go back. No command, no file edit, no restart.

From now on `iterlab demo` opens straight into GUI mode, because the interface has elements.

### The part that matters

**Leave the window open.** Change `2` to `5`, save, and click the button again.

The new curve appears. `ev.x` was never reloaded. That is the whole point: expensive loading
happens once per session, not once per edit.

Make a typo and the window stays open, tells you what broke, and lets you fix it and carry on.

---

## How it fits together

| | |
|---|---|
| **Tag** | An element's unique name, e.g. `spectrum`. Set in the editor. It is what your code sees. |
| `ev` | The session. Everything you put on it survives every edit, until the window closes. |
| `on_<interaction>_<tag>` | A handler. Write one and it is wired; there is nothing to register. |
| `ev.<tag>` | The live element, reachable by its tag. |

Every handler takes `(ev, event)`. `on_startup` takes just `(ev)`.

Handlers are **optional**. An element with no handler simply does nothing — that is normal, not an
error, and nothing is reported.

### Interactions

Available on **every** element type. Write only the ones you want:

| Handler | Fires when |
|---|---|
| `on_clicked_<tag>(ev, event)` | A mouse button is pressed on it |
| `on_hover_<tag>(ev, event)` | The pointer enters it |
| `on_motion_<tag>(ev, event)` | The pointer moves over it |
| `on_key_<tag>(ev, event)` | A key is pressed while it has focus |

Creating an element generates just one of these — click, for buttons and plot areas. Labels get
none. Add the others by hand when you want them.

### The `event` argument

| Attribute | What it is |
|---|---|
| `event.kind` | `"clicked"`, `"hover"`, `"motion"` or `"key"` |
| `event.tag` | Which element |
| `event.button` | `"left"`, `"middle"` or `"right"` |
| `event.x`, `event.y` | **Data coordinates** on a plot area; `None` elsewhere |
| `event.key` | The key, on key events |
| `event.double` | Whether a click was a double click |

`event.x` and `event.y` are in your plot's own units. Click a spectrum at 512 nm and you get
`512.0`, not a pixel offset.

---

## Elements

Three types so far. Each is drawn in the editor and reached in code as `ev.<tag>`.

### Plot area

A matplotlib `Axes`. Not a wrapper around one — the actual object, so every matplotlib call you
already know works:

```python
def on_startup(ev):
    ev.spectrum.plot(x, y, label="raw")
    ev.spectrum.set_xlabel("wavelength (nm)")
    ev.spectrum.legend()
    ev.spectrum.set_ylim(0, 1)
```

You never call `plt.show()` or `draw()` — iterlab repaints whatever your handler drew. Pan and zoom
work from the toolbar with no code at all.

| In code | |
|---|---|
| any matplotlib `Axes` method | `ev.spectrum.plot(...)`, `.clear()`, `.set_title(...)` |
| `ev.spectrum.visible` | show or hide the whole element |

Colours, fonts and borders are matplotlib's job here, so the editor offers only **Visible** for a
plot area. Style the plot itself through matplotlib.

### Button

```python
def on_clicked_run_fit(ev, event):
    ev.run_fit.text = "working..."
    ev.run_fit.enabled = False
    result = do_the_slow_thing(ev.data)
    ev.run_fit.enabled = True
    ev.run_fit.text = "Run fit"
```

| In code | |
|---|---|
| `ev.run_fit.text` | the caption (`.label` also works) |
| every style property below | |

### Label

Text placed in the layout. Set it from code — this is the usual way to show a status line:

```python
def on_clicked_run_fit(ev, event):
    ev.status.text = f"fitted in {elapsed:.1f}s"
    ev.status.text_color = "#1e7b34"
```

| In code | |
|---|---|
| `ev.status.text` | the text (`.label` also works) |
| every style property below | |

A label gets no generated handler, because a label is usually read rather than clicked. If you do
want it clickable, write `on_clicked_<tag>` yourself and it will be wired.

---

## Styling

Buttons and labels carry these. Set them **in the editor** for how the interface starts, and
**in code** to change them while it runs.

| Property | Values | Example |
|---|---|---|
| `background` | `"#rrggbb"`, `"#rgb"`, or a colour name | `ev.go.background = "#2f6feb"` |
| `text_color` | same | `ev.status.text_color = "red"` |
| `edge` | same | `ev.go.edge = "#d9a441"` |
| `edge_width` | whole number, `0` for none | `ev.go.edge_width = 2` |
| `font` | a family name, or `None` for the default | `ev.status.font = "Consolas"` |
| `font_size` | 1–200, or `None` for the default | `ev.status.font_size = 14` |
| `bold` | `True` / `False` | `ev.status.bold = True` |
| `italic` | `True` / `False` | `ev.status.italic = True` |
| `align` | `"left"`, `"center"`, `"right"` | `ev.status.align = "left"` |
| `enabled` | `True` / `False` | `ev.go.enabled = False` |
| `visible` | `True` / `False` | `ev.warning.visible = True` |

All are readable as well as writable:

```python
if not ev.go.enabled:
    ev.status.text = "still working"
```

### Where styling lives

**The editor sets the starting appearance. Code overrides it for the session.**

Assigning a style in code changes the live element and is **never written back to `demo.yaml`**.
Close and reopen, and you are back to what the editor says. That is deliberate: your layout file
stays a description of the interface, not a log of what happened to it.

The reverse is also true — moving an element in the editor never touches `demo.py`.

### In the editor

Select an element and use **PROPERTIES**:

- **COLOUR** — type a hex value, or click the swatch for a colour picker.
- **FONT** — family dropdown, size, bold, italic, alignment.
- **STATE** — visible, and enabled for buttons.

The canvas previews your choices, so you can judge them without switching modes.

---

## Changing an element's tag

Select it and edit **Tag** in the properties panel.

iterlab renames that element's handlers in `demo.py` to match. **This is the only time iterlab
modifies a line you wrote**, and it changes nothing else: comments, strings, local variables and a
handler belonging to a different element are all left exactly as they are.

If `demo.py` will not parse, the rename is refused and both files are left untouched — renaming
safely needs a readable file.

---

## Deleting an element

Select it and click **Delete element**.

Its handler stays in `demo.py`. iterlab does not delete code you wrote; remove it yourself if you
want it gone.

---

## The one gotcha

**Load your data inside `on_startup`, not at the top of the file.**

```python
import numpy as np                      # fine - cheap

data = np.loadtxt("huge.csv")           # BAD: reloads on every edit


def on_startup(ev):
    ev.data = np.loadtxt("huge.csv")    # GOOD: loads once per session
```

Picking up a code change means reloading the module, and reloading a module re-runs everything at
its top level. There is no way around that in Python. Anything inside `on_startup` is safe.

---

## What costs a restart

Almost nothing. For completeness:

| Change | Takes effect |
|---|---|
| Editing a handler | Next click. Nothing is lost |
| Adding a new handler | Next click |
| Fixing a syntax error | Next click |
| Editing `on_startup` | Toggle to the editor and back — that starts a fresh session |
| Moving or restyling an element | Toggle back to GUI mode |

A mode switch ends the session and starts a new one, so data is reloaded. Applying layout edits to
a *live* session is the aim, but it is not built yet and is not promised.

---

## Running from a script

If you would rather launch from Python or an IDE than a shell:

```python
import iterlab

iterlab.run("demo")
```

Identical to `iterlab demo`. There is deliberately no way to build a layout in code — layout is
drawn, never programmed.

---

## Known limits

Worth knowing before they surprise you.

- **A long computation freezes the window.** Handlers run to completion before the interface
  repaints. Splitting slow work across clicks is the workaround for now.
- **A mode switch reloads your data**, because it starts a fresh session.
- **Three element types so far.** Text fields, checkboxes, radio buttons, dropdowns, lists and
  sliders are not built yet.
- **Editing `demo.yaml` by hand** is possible but not the intended path; the editor is.

---

**Guide version 0.11.0.** Everything above is verified against that release. If a description here
does not match what you see, please report it — a wrong guide is worse than a missing one.
