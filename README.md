<h1><img src="https://raw.githubusercontent.com/alonhzn/iterlab/main/docs/logo.png" alt="" width="40" height="40"> iterlab</h1>


You are a **scientist**, not a software developer, **focus on what matters to you!**
Science and research are iterative processes and they require a lot of graphs, plots and inputs, data processing and algorithm revisions. IterLab is the tool that lets you focus on your work, not on the visualization and GUI code - those are made for you seamlessly. 


## What this means in practice

- **Layout is drawn, never programmed.** Drag, drop, resize. No GUI code, ever.
- **Add code? Change layout? No problem!** — We know science is iterative and constantly changes. Start with one plot and go from there. The magic happens because we create two separate files, a  `.yaml` and a `.py` sharing a name. Rearranging the interface cannot disturb your code, and editing your code cannot disturb the interface. The only link between them is an element's **tag**.
- **No need to re-run the script when you change code!** Yes you heard correctly, change your algorithm, add axis labels, no need to re-run the app, no need to reload from scratch! save hours and hours without losing anything already in memory — loaded data, computed results, and plots already drawn all survive.
- **Made a bug? Just fix it without re-running heavy code** Code bugs and typos are part of life, that doesn’t mean you should waste time re-running heavy code. Everything survives and stays in memory until you fix the code and continue from where you left off. Restarting is the cost the tool exists to remove.


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

Early, and honest about it. The end-to-end loop is implemented and tested, with five element types:
**axes, button, label, text box, number box**. Checkboxes, radio buttons, dropdowns, lists and
sliders are next.

## Built on

Tk and matplotlib, both used deliberately: Tk for every control, matplotlib for plots only.

## License

[Apache License 2.0](https://github.com/alonhzn/iterlab/blob/main/LICENSE). You may use, modify, and redistribute this code, including in
closed-source and commercial work. If you do, you must retain the copyright notice, the license,
and the [NOTICE](https://github.com/alonhzn/iterlab/blob/main/NOTICE) file, and state which files you changed.
