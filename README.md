<h1><img src="https://raw.githubusercontent.com/alonhzn/iterlab/main/docs/logo.png" alt="" width="40" height="40"> iterlab</h1>

<p align="center">And Now for Something Completely Different - A different Python paradigm that is.</p>

You are a **scientist**, not a software developer.

Research runs in a loop: load the data, plot it, change something, plot it again. An interface ought
to make that loop faster, but building one usually costs more than it saves, so the parameters end
up hard-coded and the loop turns into *edit the file, restart, wait for the data to load again*.

iterlab stops the interface and the code competing for your time and has them feed each other
instead. **The interface is drawn, not programmed**, so a box you drag onto the canvas is a
parameter you can turn while the program runs. **The code is live**, so a function you rewrite takes
effect in the window already open in front of you. **Python never restarts** — your data stays
loaded, your plots stay drawn, and you carry on from exactly where you were.

![The same interface running, being drawn in the editor, and the code behind it - each one changing the others](https://raw.githubusercontent.com/alonhzn/iterlab/main/docs/iterlab.jpg)

## What this means in practice

- **Layout is drawn, never programmed.** Drag, drop, resize. No GUI code, ever.
- **Add code? Change layout? No problem!** — We know science is iterative and constantly changes. Start with one plot and go from there. The magic happens because we create two separate files, `demo.py` for your algorithm and `demo_layout.py` for what you drew. Rearranging the interface cannot disturb your code, and editing your code cannot disturb the interface. The only link between them is an element's **tag**.
- **No need to re-run the script when you change code!** Yes you heard correctly, change your algorithm, add axis labels, no need to re-run the app, no need to reload from scratch! Save hours and hours without losing anything already in memory — loaded data, computed results, and plots already drawn all survive.
- **Made a bug? Just fix it without re-running heavy code.** Code bugs and typos are part of life, that doesn’t mean you should waste time re-running heavy code. Everything survives and stays in memory until you fix the code and continue from where you left off. Restarting is the cost the tool exists to remove.

**Watch the introduction and tutorial:**

<a href="https://www.youtube.com/watch?v=G_HzmkInHAs"><img src="https://raw.githubusercontent.com/alonhzn/iterlab/main/docs/intro.gif" width="50%" alt="iterlab introduction and tutorial - click to watch on YouTube"></a>


## Usage

```console
pip install iterlab
iterlab demo
```

One command. A new interface opens in **editor mode**: a blank canvas, a palette of element types, and
a properties panel. Drag out an axes and a button, tag them, then click the toggle in the top-left
corner to switch to **GUI mode** and use what you drew.

`demo.py` is yours. iterlab appends a handler stub for the elements that need one, and never touches
anything else. Assume an axes tagged `spectrum` and a button tagged `run_fit`:

```python
import numpy as np

def on_startup(ev):
    ev.x = np.linspace(0, 10, 500)      # loaded once per session, accessible from anywhere in your code
    ev.spectrum.plot(ev.x, np.sin(ev.x))

def on_clicked_run_fit(ev, event):
    ev.spectrum.clear()
    ev.spectrum.plot(ev.x, np.sin(2 * ev.x))
```

Edit that file **while the window is open**, click the button, and the new code runs — **no restart**, and
`ev.x` is never reloaded. Make a typo and the session survives, tells you what broke, and lets you fix
it and carry on.

`ev` is yours to fill: anything you assign to it lives for the session. Each element is reachable on
it under the tag you gave it in the designer, and an axes **is** a matplotlib `Axes` — not a wrapper
around one — so every call you already know works, and any library taking an `ax=` argument accepts
it.

**On Linux**, tkinter is packaged separately: `apt install python3-tk` or `dnf install python3-tkinter`.

**New here?** [GUIDE.md](https://github.com/alonhzn/iterlab/blob/main/GUIDE.md) walks through installing, drawing your first interface, and the
code API for every element.

## Status

Early, and honest about it. The end-to-end loop is implemented and tested, with seven element types:
**axes, button, label, text box, number box, file selector, folder selector**. Checkboxes, radio buttons, dropdowns, lists and
sliders are next.

## Built on

Tk and [matplotlib](https://github.com/matplotlib/matplotlib), both used deliberately: Tk for every control, matplotlib for plots only.
Built on the basis of my old project "rrGUI" that was never fully functional so it stayed private, and reimplemented using the remarkable framework [Spec Kit](https://github.com/github/spec-kit) and Claude.

## License

[Apache License 2.0](https://github.com/alonhzn/iterlab/blob/main/LICENSE). You may use, modify, and redistribute this code, including in
closed-source and commercial work. If you do, you must retain the copyright notice, the license,
and the [NOTICE](https://github.com/alonhzn/iterlab/blob/main/NOTICE) file, and state which files you changed.
