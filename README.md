# iterlab

**The GUI as a development environment for algorithms — not a wrapper over a finished program.**

Most GUIs are built *after* a program works, to put a friendly face on a working command-line tool.
That is one legitimate use of a GUI, and the belief that it is the *only* correct use has hidden a
second one.

In engineering and research, the GUI can be the environment in which the algorithm is *developed*.
Instead of writing a script, running it, waiting, reading numbers, closing figures, editing
constants, and running again, you draw a small interactive surface — plots, buttons, fields,
selectors — and iterate inside it. The overhead of re-running, re-loading data, re-opening figures,
and re-typing parameters moves to the interface. What remains is the algorithm.

This is the paradigm behind MathWorks GUIDE and App Designer. It is close to unknown in Python.

## What this means in practice

- **Layout is drawn, never programmed.** Drag, drop, resize. No GUI code, ever.
- **Layout and algorithm are separate files** — a `.yaml` and a `.py` sharing a name. Rearranging
  the interface cannot disturb your code, and editing your code cannot disturb the interface. The
  only link between them is an element's tag.
- **Code edits take effect immediately**, without relaunching, and without losing anything already
  in memory — loaded data, computed results, and plots already drawn all survive.
- **The process does not die on your account.** A control with no code behind it yet, or a syntax
  error mid-edit, never takes the session down. Restarting is the cost the tool exists to remove.

## Usage

```console
pip install iterlab
iterlab demo
```

One command. A new interface opens in **editor mode**: a blank canvas, a palette of element types, and
a properties panel. Drag out a plot area and a button, name them, then click the toggle in the
top-left corner to switch to **GUI mode** and use what you drew.

`demo.py` is yours. iterlab appends one handler stub per element and never touches anything else:

```python
import numpy as np

def on_startup(ev):
    ev.x = np.linspace(0, 10, 500)      # loaded once per session
    ev.spectrum.plot(ev.x, np.sin(ev.x))

def on_clicked_run_fit(ev, event):
    ev.spectrum.clear()
    ev.spectrum.plot(ev.x, np.sin(2 * ev.x))
```

Edit that file while the window is open, click the button, and the new code runs — no restart, and
`ev.x` is never reloaded. Make a typo and the session survives, tells you what broke, and lets you fix
it and carry on.

`ev` is yours to fill: anything you assign to it lives for the session. Each element is reachable on it
under the name you gave it in the designer, and a plot area *is* a matplotlib `Axes`, so you use the
API you already know.

**On Linux**, tkinter is packaged separately: `apt install python3-tk` or `dnf install python3-tkinter`.

**New here?** [GUIDE.md](GUIDE.md) walks through installing, drawing your first interface, and the
code API for every element.

## Status

Early, and honest about it. Feature 001 — the end-to-end loop — is implemented and tested, with two
element types. Text boxes, labels, radio buttons, dropdowns, lists and sliders are next.

Known limits, all recorded rather than hidden: switching modes ends the session, so a layout edit costs
a data reload; long computations block the window; and data loaded at module level rather than inside
`on_startup` reloads on every edit.

The project was specified before it was built — see
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) for the principles that govern it,
each traceable to a documented failure of an earlier prototype.

## Built on

Tk and matplotlib, both used deliberately: Tk for every control, matplotlib for plots only.
Minimal dependencies is a constraint, not an aspiration.

## License

[Apache License 2.0](LICENSE). You may use, modify, and redistribute this code, including in
closed-source and commercial work. If you do, you must retain the copyright notice, the license,
and the [NOTICE](NOTICE) file, and state which files you changed.
