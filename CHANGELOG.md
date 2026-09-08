# Changelog

All notable changes to iterlab are recorded here. The project follows semantic
versioning as defined in the project constitution's *Release And Versioning*
section, where the public surface is larger than the Python API: the layout
schema, the handler naming convention, the `ev` contract, the generated stub
shape, and the command are all consumed directly by researcher-written code.

## [0.2.0] — unreleased

Everything found by the first hands-on session with the application. Each of the
four defects below was a component that was fully implemented and never
connected to anything, and each was invisible to the automated suite because the
tests exercised the mechanism directly rather than going through the assembled
app.

### Fixed

- The mode toggle did nothing. `ModeToggle` was written but never instantiated,
  so the chrome frame held no control at all.
- `ev.some_plot.plot(...)` drew nothing after the first interaction. An embedded
  figure gets no automatic repaint — pyplot installs that hook and pyplot has no
  place here, since `plt.show()` would start a second event loop against Tk's.
  Handlers now repaint whatever they drew.
- A launch-time fault in startup was reported twice, because the deferred-startup
  hook re-entered itself.
- Adding an element to a `.py` written with CRLF line endings rewrote every line
  in the file.

### Added

- Drag an element to move it; drag an edge to resize one dimension or a corner
  to resize both. Pointer feedback says what a press will do before you commit.
- Click empty canvas to place an element at a sensible default size for its
  type, centred on the click. Escape deselects, since clicking now creates.
- `iterlab.run(name)` — the library entry point that contracts/commands.md and
  the README had documented while `__init__.py` was empty.
- The version has a single source of truth in `__init__.py`, which
  `pyproject.toml` reads.

## [0.1.0] — unreleased

The initial implementation of feature 001. Never published; superseded by 0.2.0
before it left the working tree.

### Added

- `iterlab <name>` opens an interface. One command; editing and using it are two
  modes of one program, switched with the toggle in the top-left corner.
- **Editor mode**: a canvas, a palette of element types, and a properties panel.
  Draw by dragging; every property is editable, including the name.
- **GUI mode**: the interface as drawn, with handlers wired and the standard
  matplotlib navigation toolbar on every plot area.
- Two element types: plot areas and buttons.
- Handlers bind by naming convention (`on_<interaction>_<element>`), with the
  universal interaction set click / hover / motion / key. Every handler is
  optional; exactly one stub is generated per element.
- Code changes take effect on the next interaction with no restart, and nothing
  in the session is discarded — loaded data, computed results and drawn plots
  all survive.
- A fault in researcher code never ends the session. It is reported to stderr
  in full and signalled in the window, and the report clears when corrected code
  runs. An element with no handler is silent, which is a different thing.
- Renaming an element rewrites its handlers and nothing else in the file.
- Layout files record `schema_version: 1`. A layout written by a newer iterlab
  is reported and left untouched rather than partially understood.

### Known limits

- A mode switch ends the session; switching back runs startup again. Applying
  layout edits to a live session is the aim, not a promise.
- Changing `on_startup` takes effect by starting a fresh session — toggling out
  and back is enough.
- Handlers run to completion while the interface waits. Long computations block
  the window.
- Reloading a module re-executes its top level, so data loaded at module level
  rather than in `on_startup` will reload on every edit. The generated starter
  file says so.
