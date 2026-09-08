# Changelog

All notable changes to iterlab are recorded here. The project follows semantic
versioning as defined in the project constitution's *Release And Versioning*
section, where the public surface is larger than the Python API: the layout
schema, the handler naming convention, the `ev` contract, the generated stub
shape, and the command are all consumed directly by researcher-written code.

## [0.11.1] — unreleased

### Fixed

- A UI test asserted real OS focus, which the window manager can withhold and
  which other tests disturb by mapping and unmapping the shared Tk root. It
  passed alone and failed in the full suite. Now asks Tk which widget is last
  focused *for that toplevel*, which is the same question without depending on
  the desktop.

## [0.11.0] — unreleased

### Added

- **`GUIDE.md`** — a user guide: install, first interface, the handler and `ev`
  model, every element type with its code API, the full styling table, tagging,
  deleting, and the known limits. It will grow as element types are added.

### Fixed

- A plot area's `visible` could be set but not read. `PlotHandle` delegates
  unknown attributes to its matplotlib `Axes`, which knows nothing about
  `visible`, so reading it raised `AttributeError` while writing it worked. Any
  style property a handle can set is now also readable — found while checking
  the guide's claims rather than by writing them down and hoping.

## [0.10.0] — unreleased

### Fixed

- Clicking, hovering or typing on a **plot area** raised `NameError: name
  'name' is not defined`. The v0.8.0 tag rename missed the closure inside
  `build_plot_area`, which still referred to `name` and still passed
  `element=` to an `Event` whose field had become `tag`. Plot areas were the
  only element type affected.

### Added

- `tests/ui/test_plot_events.py` drives matplotlib's own callback machinery —
  the closures in `build_plot_area` — rather than calling the dispatcher
  directly. Every other plot test went straight to the dispatcher, so the
  closures were never executed and a NameError in them survived a 291-test
  suite. Seven of the eight new tests fail against the bug.

## [0.9.0] — unreleased

### Added

- **Style properties on buttons and labels**: fill colour, text colour, border
  colour and width, font family, font size, bold, italic, alignment, enabled
  and visible. A plot area takes only `visible` — matplotlib owns the rest of
  how it looks, and offering a fill colour that did nothing would be a lie.
- **Every style property is settable from code**, and doing so changes the live
  widget without ever writing back to the layout file. The layout holds the
  *starting* appearance; research code overrides it for the session:

      ev.title.background = "#ffe0e0"
      ev.title.font_size = 20
      ev.run_fit.enabled = False

- Editors for all of it in the properties panel: hex fields with a swatch that
  opens the system colour picker, a font dropdown listing only families
  actually installed, and checkboxes and radio buttons for the rest.
- The editor canvas now previews an element's real colours, font and weight, so
  a styling choice can be judged without toggling to GUI mode.

### Changed

- **Layout schema version 2.** The `style` block is new, and an older build
  would reject it as an unrecognized key, so the version had to move — and with
  it comes the first real migration (FR-036c said to write one when it was
  actually needed rather than in advance). A version 1 layout opens unchanged,
  is migrated in memory, and is only rewritten when something is saved.
- Only non-default style values are written, so an unstyled element is still a
  three-line entry.

## [0.8.0] — unreleased

### Changed

- An element's unique identifier is now called its **tag**, everywhere. It was
  "name", which collided with the interface's own name and with the handler
  *function* names it appears in. The legacy 2024 spike called it a tag too.

  Researcher-facing: `event.element` becomes `event.tag`; the properties panel
  field is "Tag". Unchanged: `ev.<tag>`, `on_clicked_<tag>` and the layout file
  format — the tag has always been the mapping key there, so **no existing
  layout or research code needs editing**.

  Internally `Element.name` becomes `Element.tag`, `Layout.names()` becomes
  `Layout.tags()`, `Layout.rename()` becomes `Layout.retag()`, and
  `validate_name` becomes `validate_tag`. Deliberately *not* renamed:
  `Interface.name`, which is the interface's own name, and `handler_name`,
  which really is a function's name.

## [0.7.0] — unreleased

### Fixed

- Resize cursors did nothing on Linux. `size_nw_se` and `size_ne_sw` are Tk's
  Windows-only names; X11 has no such cursors, so every diagonal handle showed
  no pointer change at all. The guard in `_set_cursor` caught the error and
  said nothing. Replaced with X11 corner names, which all three platforms
  accept — and which give each corner its own cursor rather than sharing one
  across a diagonal. Found by CI on Linux.

### Added

- `tools/verify.py` builds a throwaway interface for the manual verification
  pass: a plot, a label and two buttons, with research code that loads slowly,
  plots, and fails on demand. It removes the setup from Gate 2, which was the
  real reason the pass had never been done.
- A test asserting every cursor name is valid on the running platform. Tk
  silently ignores an unknown one, so nothing else would report it.

## [0.6.0] — unreleased

### Added

- A **label** element: text placed in the layout and set from code with
  `ev.status.text = "..."`. It is the first type with **no generated handler** —
  a label displays text rather than being clicked, and a stub for every one
  would leave a pile of dead functions in the researcher's file. Every
  interaction is still available if the handler is written by hand (FR-017a);
  only the automatic stub is withheld.

### Changed

- The editor opens at 1080x760 rather than the interface's own size. That size
  describes the *interface*, and is advisory; editor mode adds a sidebar the
  interface knows nothing about. Switching to the editor grows a window that is
  too small but never shrinks one — a size chosen deliberately stays.
- The default button is smaller: roughly 134x38 px on a maximised 1920x1080
  window, down from 230x65, which read as unusually large.
- Palette entries are single compact rows of icon and name, about 33 px each,
  rather than cards with descriptions. The vocabulary is going to grow, and a
  card tall enough for a description does not survive a dozen types in a
  sidebar.
- The text field in the properties panel now serves any text-bearing type, not
  just buttons. `label` holds a button's caption and a label's text — the same
  idea, so it stays one schema field rather than two.

## [0.5.0] — unreleased

### Added

- Generated starter files import numpy as np. No research happens without it.
- A delete control in the properties panel, pinned to the bottom of the sidebar
  so a destructive action is never the thing pushed off the screen. The
  element's handler stays in the code file, as it always has.
- The editor sidebar scrolls when its contents are taller than the window.

### Changed

- The editor has a modern look: the `clam` ttk theme restyled with a flat
  palette, the element types shown as icon cards rather than radio buttons, and
  the geometry fields laid out as a 2x2 grid instead of four stacked rows.
  Icons are drawn as vectors rather than loaded from image files or set as text
  glyphs — no assets to ship, and no bet on the platform font having a
  character.
- Property edits commit on Enter or when the field loses focus. The Apply
  button is gone: a value typed and tabbed away from is a value you meant.
- Removed the dashed "mode toggle" hint from the canvas. The toggle lives in
  its own chrome bar above the layout, so nothing is ever underneath it and the
  hint was misleading.

### Fixed

- The sidebar's contents disappeared at small window sizes. Tk stops *mapping*
  children that no longer fit rather than clipping them, so the geometry fields
  were absent rather than scrolled out of view — with no error, no scrollbar,
  and the only symptom being that typing into them did nothing. At the 800x450
  default this affected every position field.

## [0.4.0] — unreleased

### Fixed

- A button responded only to the left mouse button. Middle and right clicks did
  not reach the handler at all — Tk's `command` option fires for button 1 only,
  and nothing else was bound. The event also reported `"left"` unconditionally,
  since the value was hardcoded rather than read from the click. All three
  buttons now fire the handler and `event.button` says which one.
- Removed `_bind_tk_events`, which was written but never called.

### Changed

- The generated stub for a plot area now prints which mouse button was used
  alongside the coordinates, and its comment lists the possible values. The
  button was always available on the event; nothing advertised it.

## [0.3.0] — unreleased

### Changed

- Placing an element no longer opens a modal asking for its name. The element
  is created with its default name, selected, and the properties panel's name
  field is focused with the text selected — so accepting the default needs no
  typing and replacing it needs no extra click. This still satisfies FR-005a,
  and it removes a dialog that stopped the researcher on every placement.

### Fixed

- The test suite could stop and wait for a human. One code path opened a modal
  that no test stubbed, which made the suite unrunnable unattended and so
  disqualified it as a release gate (Principle VII, Gate 1). The dialog is
  gone, and `tests/conftest.py` now makes any modal — dialog, message box or
  file chooser — raise instead of block, so a future one fails loudly rather
  than appearing to hang.

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
