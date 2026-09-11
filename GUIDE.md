<h1><img src="docs/logo.png" alt="" width="40" height="40"> iterlab user guide</h1>


The GUI as a place to *develop* an algorithm, not a wrapper you bolt on afterwards.

You draw the interface. You write the algorithm. iterlab keeps the two in separate files and gets
out of the way — including staying alive while you edit, so you stop paying to restart.

> This guide grows with the tool. It documents what works **today**, in the version named at the
> bottom. If something here does not behave as described, that is a bug — please say so.

---

## Install

```console
pip install iterlab
```

Or from source, if you want to change iterlab itself:

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

Draw an **Axes** and a **Button**. They will be tagged `ax_0` and `cmd_0`.

`demo.py` now ends with a handler for each. iterlab appends; it never edits or removes anything you
wrote.

Prefer better names? Rename them in the editor at any point and iterlab renames the handlers to
match. The examples below use `ax_0` and `cmd_0` because that is what you just drew.

### Write the algorithm

Open `demo.py` in your own editor:

```python
import numpy as np


def on_startup(ev):
    # Runs once when the interface opens. Load your data HERE, not at the top
    # of the file - see "The one gotcha" below.
    ev.x = np.linspace(0, 10, 500)
    ev.ax_0.plot(ev.x, np.sin(ev.x))


def on_clicked_cmd_0(ev, event):
    ev.ax_0.clear()
    ev.ax_0.plot(ev.x, np.sin(2 * ev.x))
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
| `ev` | The session. Everything you put on it survives every edit and every mode switch, until you restart it or close the window. |
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
| `on_changed_<tag>(ev, event)` | A box's value is committed — Enter, or leaving it after an edit |

Creating an element generates just one of these: **click** for buttons, axes and the two selectors,
**changed** for text and number boxes. A label gets none, because it is written to rather than
interacted with. Add any of the others by hand whenever you want them.

### The `event` argument

| Attribute | What it is |
|---|---|
| `event.kind` | `"clicked"`, `"hover"`, `"motion"` or `"key"` |
| `event.tag` | Which element |
| `event.button` | `"left"`, `"middle"` or `"right"` |
| `event.x`, `event.y` | **Data coordinates** on an axes; `None` elsewhere |
| `event.key` | The key, on key events |
| `event.double` | Whether a click was a double click |

`event.x` and `event.y` are in your plot's own units. Click a spectrum at 512 nm and you get
`512.0`, not a pixel offset.

---

## Elements

Seven types so far. Each is drawn in the editor and reached in code as `ev.<tag>`.

New elements are tagged by type — `ax_0`, `cmd_0`, `lbl_0`, `edt_0`, `val_0` — and numbered upward.
The two selectors are the exception: the first is just `fileselect` and `folderselect`, with no
number, because an interface almost always has one of each. A second becomes `fileselect_1`.
Rename any of them in the editor.

**Every element that shows text has `.text`**, whatever kind it is. You never have to remember
whether `ev.status` is a label or a box to read what it says:

```python
ev.lbl_0.text = "Fitting..."      # a label
ev.cmd_0.text = "Stop"            # a button caption
path = ev.edt_0.text               # what someone typed
```

### Axes

A matplotlib `Axes`. Not a wrapper around one — **the actual object**, so every matplotlib call you
already know works, and any library that takes an `ax=` argument accepts it:

```python
def on_startup(ev):
    ev.ax_0.plot(x, y, label="raw")
    ev.ax_0.set_xlabel("wavelength (nm)")
    ev.ax_0.legend()
    ev.ax_0.set_ylim(0, 1)
```

You never call `plt.show()` or `draw()` — iterlab repaints whatever your handler drew. Pan and zoom
work from the toolbar with no code at all.

| In code | |
|---|---|
| any matplotlib `Axes` method | `ev.ax_0.plot(...)`, `.clear()`, `.set_title(...)` |
| `ev.ax_0.visible` | show or hide the whole element, toolbar included |

```python
isinstance(ev.ax_0, matplotlib.axes.Axes)   # True
seaborn.histplot(data, ax=ev.ax_0)          # works, because it really is one
```

Colours, fonts and borders are matplotlib's job here, so the editor offers only **Visible** for an
axes. Style the plot itself through matplotlib.

`ev.ax_0.visible` means what it means on every other element — is this thing on screen — and hides
the axes together with its toolbar. matplotlib's own `set_visible` is untouched and still does
matplotlib's thing, which is to hide the axes but leave the frame around it.

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

### Text box

A line of text someone types. Read it in a handler for something else — usually a button:

```python
def on_clicked_cmd_0(ev, event):
    ev.data = np.loadtxt(ev.edt_0.text)      # whatever they typed
    ev.lbl_0.text = f"loaded {len(ev.data)} rows"
```

| In code | |
|---|---|
| `ev.edt_0.text` | the contents; assign to it to prefill or clear the box |
| every style property below | |

It starts empty, because any other default would be text you have to delete first.

### Number box

The same, but it will not accept anything that is not a number. Typing letters into it does nothing —
the character never appears — while a minus sign and a decimal point are allowed anywhere they could
still lead to a number.

```python
def on_clicked_cmd_0(ev, event):
    ev.result = fit(ev.data, threshold=ev.val_0.value)
```

| In code | |
|---|---|
| `ev.val_0.value` | the **number**: `8` from `"8"`, `12.5` from `"12.5"`, `0` from an empty box |
| `ev.val_0.text` | the same thing as a string, so it behaves like every other element |
| every style property below | |

`.value` gives a whole number back as an `int`, so `range(ev.val_0.value)` works without casting. An
empty box reads as `0` rather than raising: someone who cleared it to retype is mid-edit, not
mistaken.

**Both boxes get an `on_changed_<tag>` handler**, which fires when you **finish** entering a value —
not on every keystroke:

```python
def on_changed_val_0(ev, event):
    ev.ax_0.clear()
    ev.ax_0.plot(ev.x, np.sin(ev.val_0.value * ev.x))
```

Two things run it, and they are not treated the same:

| | |
|---|---|
| **Enter** | Always runs it. That is also how you re-run the same value on purpose |
| **Leaving the box** | Runs it only if you actually changed something. Clicking past a box on the way somewhere else does nothing |

Per keystroke would redraw once for `1`, again for `10`, again for `100` — expensive, and two of those
plots are of a number nobody meant. If you do want every keystroke, `on_key_<tag>` is still there.

The generated handler just prints the value, so you can see it working before you write anything.
Delete it if you would rather read the box when a button is clicked instead — nothing breaks.

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

Empty means empty. Clear a label's text, in the editor or with
`ev.status.text = ""`, and it shows nothing — useful for a status line that
should stay blank until there is something to say. The editor still writes the
tag on it so you can find it on the canvas; your interface does not.

A label gets no generated handler, because a label is usually read rather than clicked. If you do
want it clickable, write `on_clicked_<tag>` yourself and it will be wired.

### File select

A button that opens your operating system's own file chooser — the one you already know, with your
places and network drives in it.

```python
def on_clicked_fileselect(ev, event):
    ev.lbl_0.text = ev.fileselect.path
    ev.data = np.loadtxt(ev.fileselect.path)
```

| In code | |
|---|---|
| `ev.fileselect.path` | the chosen file, or `""` if there isn't a usable one |
| `ev.fileselect.extensions` | which file types the chooser offers, e.g. `"txt, csv"` |
| `ev.fileselect.text` | the button's caption, like any button |
| every style property below | |

**It remembers.** The last choice comes back next time you open the interface — after a hard reset,
and after closing the program entirely. Nothing is written into your project folder; the memory
lives in your own user directory (`%LOCALAPPDATA%\iterlab` on Windows,
`~/Library/Application Support/iterlab` on macOS, `~/.local/state/iterlab` on Linux), keyed by where
the interface is. Move or copy the project and it simply starts fresh.

**The caption never changes.** The button still says "Select a File" after a choice — showing the
selection is one line in your handler, which is why the generated stub shows it. That keeps how your
interface looks something you decide rather than something that changes under you.

**`.path` is `""` when the file has gone.** Not just before the first choice: if what you picked was
deleted or moved, `.path` is empty rather than a path that no longer resolves. So `if
ev.fileselect.path:` is always the right check. The chooser still opens where the file used to be.

**Filtering by type.** Set **Types** in the editor, or `ev.fileselect.extensions` in code, to a
comma-separated list: `txt, jpeg, png, csv`. Leading dots, capitals and stray spaces are all fine
(`.TXT` works). Blank shows every file. "All files" is always offered as well, so a filter can never
trap you when the one file you need was saved with the wrong suffix.

### Folder select

The same, for a directory.

```python
def on_clicked_folderselect(ev, event):
    ev.out_dir = ev.folderselect.path
```

| In code | |
|---|---|
| `ev.folderselect.path` | the chosen folder, or `""` |
| `ev.folderselect.text` | the caption |
| every style property below | |

It remembers and falls back exactly as the file selector does, and has no **Types** — filtering a
folder chooser by file type would mean nothing.

Both fire `on_clicked_<tag>` **after** a choice, so `.path` is already set when your code runs.
Cancelling the dialog does nothing at all: no handler, no change.

---

## Styling

Buttons, labels, text boxes and number boxes all carry these. Set them **in the editor** for how the
interface starts, and **in code** to change them while it runs. (An axes carries only `visible`;
matplotlib owns the rest of how a plot looks.)

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

Assigning a style in code changes the live element and is **never written back to `demo.yaml`**. It
survives mode switches, because that is the same session — but close the window, or press **Hard
reset**, and you are back to what the editor says. That is deliberate: your layout file stays a
description of the interface, not a log of what happened to it.

The reverse is also true — moving an element in the editor never touches `demo.py`.

### In the editor

Select an element and use **PROPERTIES**. It shows the essentials — the **tag**, and the **text** for
anything that shows text. Everything else is behind **More**, which opens a drawer with position and
size, colour, font and state.

The drawer stays open once you open it, so adjusting colours across several elements does not mean
reopening it each time.

- **COLOUR** — type a hex value, or click the swatch for a colour picker.
- **FONT** — family dropdown, size, bold, italic, alignment.
- **STATE** — visible, and enabled for anything a person can interact with.

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
| Moving, restyling, adding or deleting an element | Toggle back to GUI mode. Nothing is lost |
| Editing `on_startup` | iterlab notices and offers to re-run it — see below |
| Editing a module you `import` | **Hard reset** |

**Switching modes costs you nothing.** Your data stays on `ev`, your plots keep what you drew on
them, and `on_startup` does not run again. Draw a new button, come back, and the session you were
in the middle of is still there.

That includes what your elements are *showing*: text somebody typed into a box, a caption or colour
your code set. Those survive the switch too, so nudging a button never costs you a retyped filename.

The one exception is deliberate — if you **edit** a property in the editor, your edit wins. Change a
button's caption there and the old one does not come back.

### When you edit `on_startup`

Every other handler takes effect on your next click, because your next click is what runs it.
`on_startup` is the exception — it already ran, when the session began. So editing it does nothing
at all until something re-runs it, and nothing goes wrong to tell you so.

iterlab watches the file for it. **Save `on_startup` and, within a second, the interface says so on
its own** — the **Re-run startup** button in the top bar comes alive, and a strip appears at the
bottom offering:

| | What it does | When you want it |
|---|---|---|
| **Re-run startup** | Runs the new `on_startup` over the session you already have. Your data stays | Almost always. This is the cheap one |
| **Hard reset** | Throws everything away and starts cold | When re-running would not be safe — see below |
| **Dismiss** | Nothing. Hides the strip | When you know the edit does not matter yet |

You do not have to click anything for this to appear, and it does not matter whether the element you
click has a handler. Saving is enough.

The notice also appears if you edit a **function that `on_startup` calls**, since that changes what
startup does just as surely. Editing an ordinary handler never raises it, and neither does a file
caught mid-keystroke that will not parse yet.

**When re-running is not safe.** Re-running does not clear anything first, so startup code that
*accumulates* will do it twice:

```python
def on_startup(ev):
    ev.x = np.loadtxt("huge.csv")   # safe to re-run: assigning replaces
    ev.log.append("started")        # NOT safe: appending adds a second entry
    ev.conn = open_connection()     # NOT safe unless it closes the old one
```

The idiom this guide teaches — assign onto `ev` — is safe. If yours accumulates, use **Hard
reset** instead. iterlab offers both rather than choosing for you, because only your code knows which
it is.

Dismissing does not mark the edit as accepted: change `on_startup` again and the notice comes back.

### Hard reset

**Hard reset** sits next to the toggle, in both modes. It is the big hammer, and it does what
re-launching `iterlab demo` would do without closing the window:

- your layout is re-read **from the file**, so a hand edit to `demo.yaml` is picked up
- your code is loaded fresh
- `ev` is emptied and `on_startup` runs again

You stay in whichever mode you pressed it in, and the window is not resized.

Reach for it when a warm reload is not enough — most often after editing a **module you import**.
iterlab assumes imported modules do not change during a session, so if you split your work across
`demo.py` and `fitting.py`, edits to `fitting.py` are not picked up. Hard reset is the answer.

Every button in the top bar has hover text saying exactly what it will do, because two of them
differ only in how much they throw away.

---

## Saving a picture

**Screenshot** in the top bar writes a PNG next to your `.py` and `.yaml`, named `demo-<date>-<time>.png`.

It captures your interface only — the top bar with iterlab's own buttons is left out, because it is
this tool's furniture and not part of what you built.

## Positions and sizes

Everything positional is held to **two decimals** — hundredths of the window. Drag something and its
position lands on that grid, in the editor and in the file alike.

Finer than a hundredth is below what you can place by hand and below what you can see, and it turns
`demo.yaml` into a wall of digits whose diffs mean nothing. If you type `0.333` into a position
field, you will get `0.33`.

## Running it from your IDE

`demo.py` ends with this, and it is there from the moment the file is created:

```python
if __name__ == "__main__":
    import iterlab

    iterlab.run(__file__)
```

So you can press your IDE's run button on `demo.py` and get your interface — no terminal, nothing to
remember. `iterlab demo` does exactly the same thing.

It passes `__file__` rather than a name, so it works whatever directory you run from and keeps
working if you rename the pair. And it cannot loop: iterlab loads your module under a name of its
own, so `__name__` is only `"__main__"` for the copy you launched.

New handlers are added **above** this block, so it stays at the bottom where it reads as the end of
the file.

Interfaces created before iterlab 1.2.0 do not have it — iterlab only ever adds handlers to your
file, so it will not retrofit this. Paste it in yourself if you want it.

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
- **Seven element types so far.** Checkboxes, radio buttons, dropdowns, lists and sliders are not
  built yet.
- **Modules you import are assumed not to change** while the session runs. Editing a helper module
  of your own has no effect until you press **Hard reset**.
- **Editing `demo.yaml` by hand** is possible but not the intended path; the editor is.

---

**Guide version 1.3.2.** Everything above is verified against that release. If a description here
does not match what you see, please report it — a wrong guide is worse than a missing one.
