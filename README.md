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
  only link between them is an element's name.
- **Code edits take effect immediately**, without relaunching, and without losing anything already
  in memory — loaded data, computed results, and plots already drawn all survive.
- **The process does not die on your account.** A control with no code behind it yet, or a syntax
  error mid-edit, never takes the session down. Restarting is the cost the tool exists to remove.

## Status

Early. The project is being specified before it is built — see
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) for the principles that govern
it, each traceable to a documented failure of an earlier prototype.

## Built on

Tk and matplotlib, both used deliberately: Tk for every control, matplotlib for plots only.
Minimal dependencies is a constraint, not an aspiration.

## License

TBD.
