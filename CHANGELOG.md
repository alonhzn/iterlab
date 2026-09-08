# Changelog

All notable changes to iterlab are recorded here. The project follows semantic
versioning as defined in the project constitution's *Release And Versioning*
section, where the public surface is larger than the Python API: the layout
schema, the handler naming convention, the `ev` contract, the generated stub
shape, and the command are all consumed directly by researcher-written code.

## [0.20.2] — unreleased

### Documentation

- **The logo now heads `README.md` and `GUIDE.md`**, from `docs/logo.png`.

- **Both documents brought back in line with the code.** Everything below was
  wrong, not merely dated:

  - `README.md` said `pip install iterlab`. It is not on PyPI, and the guide
    said so two paragraphs later in a different file. Now both give the
    repository install.
  - `README.md` claimed "two element types" with "text boxes, labels ... next".
    There are five, and text boxes and labels are two of them.
  - `GUIDE.md` told the reader to draw `ax_0` and `cmd_0` and then showed an
    example using `ev.spectrum` and `on_clicked_run_fit` — tags it had never
    asked anyone to create. The worked example now uses the tags it just named,
    and says renaming is available.
  - Two leftovers from a careless find-and-replace: "use **Restart reset**" and
    "press **Restart app**", for a button now called **Hard reset**.
  - "Buttons and labels carry these" under Styling, written before boxes
    existed and never revisited.
  - Stubs were described as generated for "buttons and plot areas", with
    "plot areas" long since renamed and boxes never mentioned.
  - The styling note said code-set style is lost when you "close and reopen".
    True, but it now survives a mode switch, which is the case a researcher
    actually meets.

- Every code example in the guide was executed against this build — startup,
  the click handler, all eleven style properties, `.text` on each type, and
  `.value` on a number box — rather than read over. No fault was raised by any
  of them.

## [0.20.1] — unreleased

### Fixed

- **A mode switch reset every element to its layout value.** Text typed into a
  box, and a caption, colour or enabled-state set from code, all reverted on the
  way back from the editor. Reported as "gui objects get reset when going to
  editor".

  The session introduced in 0.12.0 kept `ev` and the contents of each plot, but
  not the widgets' own state — and a switch destroys every widget and builds new
  ones from the layout file, so anything the *running* interface had done was
  lost. The layout is where an element starts, not where it currently is.

  Each handle can now report its presentation and have it restored; the session
  holds it across the switch. Programmatic style was reverting too, which was
  not in the report but is the same defect.

  **An edit in the editor still wins.** The remembered value is recorded
  alongside the layout value it was based on, so if the researcher has since
  changed the caption or the colour themselves, the remembered one is dropped —
  editing a button's caption and having the old one come straight back would be
  its own bug report. Position is not presentation, so moving an element does
  not discard what it was showing.

  A **hard reset** still clears everything, which is the difference between
  restarting and toggling.

  14 tests; 10 of them fail against the unfixed code.

## [0.20.0] — unreleased

### Added

- **Two new element types: `text_box` and `number_box`.** A text box holds a
  line someone types; a number box refuses anything that is not a number.

  The number box validates the *proposed* contents on each keystroke rather than
  correcting afterwards, so a rejected character never appears at all — no
  flicker, and the box is never momentarily holding something that is not a
  number. It deliberately accepts the half-written states a person passes
  through: `""`, `"-"`, `"."` and `"-."` are all on the way to a number, and
  refusing them would make a negative or a decimal impossible to type.

  `.value` gives the number — `int` when it is a whole one, so
  `range(ev.val_0.value)` works without casting — and an empty box reads as `0`
  rather than raising, since someone who cleared it to retype is mid-edit, not
  mistaken. `.text` gives the same thing as a string.

  Neither gets a generated stub, for the reason a label does not: a box is
  normally read when something *else* happens rather than reacted to keystroke
  by keystroke. Every interaction remains available to a hand-written handler.

- **`.text` on every element that shows text**, whatever kind it is. A button
  and a label keep their string in Tk's `-text` option and a box keeps it in a
  variable; `.text` hides that, so `ev.<tag>.text` works without first
  remembering what `<tag>` is.

### Changed

- **Default tags are now short and typed**: `cmd_0` for a button, `lbl_0` for a
  label, `edt_0` for a text box, `val_0` for a number box (`ax_0` unchanged).
  These are the shorthands a person would use themselves, so `ev.cmd_0` reads
  the way the code around it already does.

- **New elements come with working text**: a button says "Click here!" and a
  label says "Information:", rather than repeating their own tag. A button
  reading `cmd_0` is a placeholder the researcher has to fix before showing
  anyone; one reading "Click here!" is a control. The default button is slightly
  wider to fit its caption — a default that clips its own text is worse than one
  that is a little roomy.

- **Layout schema 3 → 4.** Nothing in an existing file changes and the migration
  is a no-op, but the version has to move: a file written now may contain a type
  a version-3 build has never heard of, and the version gate is what makes that
  build refuse the file cleanly rather than report an unknown element type as a
  defect in the researcher's layout.

## [0.19.1] — unreleased

### Fixed

- **The window icon did not appear.** Tk offers two mechanisms — `iconbitmap`
  with an `.ico` and `iconphoto` with a `PhotoImage` — and 0.18.0 applied both
  "for coverage". They do not layer: applied together to one window the title
  bar shows a blank grey square, which is worse than either alone and worse than
  doing nothing. Each works perfectly on its own.

  Exactly one is applied now, chosen by platform: `iconbitmap` on Windows, so
  each size gets the frame drawn for it and the title bar shows the 16 px
  artwork rather than Tk squeezing down the 256; `iconphoto` elsewhere, which is
  what X11 and macOS honour. The other is tried only when the first *fails*, as
  a fallback rather than a supplement.

  The test that existed asserted `apply()` returned True — which it happily did
  while producing an empty box. It is the same shape of defect as every wiring
  bug in this project: the mechanism was tested and the outcome was not. The
  test now counts which Tk calls are actually made and fails if both are, and
  Gate 2 gained an item to look at the title bar, since only a person can tell a
  drawn icon from a blank one.

## [0.19.0] — unreleased

### Changed

- **The icon is redrawn from a supplied logo**: a waveform ringed by two arcs
  chasing each other. The wave is the researcher's data, the ring is the loop
  they work inside, which is a better statement of the tool than the previous
  drawing managed.

  Two things carry it. The ring takes an **angular** gradient whose colour run
  is mapped onto each arc's own sweep, so a tail is fully dark and an arrow head
  fully bright — spread over a half-turn instead, both ends land mid-blue and
  the heads lose their punch. The wave takes a **linear** gradient, because it
  travels where the ring turns.

  The detail thresholds moved after looking at the frames magnified rather than
  guessing: at 64 px the dotted arcs had already collapsed into a grey fuzz that
  made the whole mark look dirty, so the full drawing now starts at 128.

  **The 16 and 24 px frames invert** — a white wave on solid brand blue. A dark
  line on a near-white tile has almost no ink left to work with at that size and
  goes faint in a taskbar, where the light tile's own edge is lost too. It
  trades a little consistency between sizes for a mark that can be seen, and
  nobody views the 16 and the 256 side by side.

## [0.18.0] — unreleased

### Added

- **An application icon**, replacing Tk's default feather — which tells a
  researcher nothing and makes the window look like a stray interpreter in a
  taskbar full of real applications.

  A plot with a loop: the rising curve is every plotting library's icon, and the
  circular arrow is what makes it this one, since iterating inside the interface
  rather than re-running a script is the whole product.

- `tools/make_icon.py`, which *is* the icon — checked in as the source rather
  than a binary somebody would have to open an image editor to change.

  It draws at 8x and downsamples, and brushes strokes as overlapping discs
  rather than using `draw.line`, which leaves notches exactly where this curve
  turns. The `.ico` carries **three detail levels across seven sizes**: below
  48 px the axes are dropped and the brush fattens, and at 16 px only the curve
  survives. An icon is not one drawing scaled — the thin marks close into mud —
  and a test asserts the 16 px frame is not merely the 256 resampled.

  Applied through both `iconphoto` (portable, honoured by X11 and macOS) and
  `iconbitmap` (what Windows uses for the title bar and taskbar, and crisper
  there). Neither can raise: an icon is decoration, and decoration must not be
  able to end a session. The `PhotoImage` is held for the life of the process,
  since Tk silently reverts to the feather when one is collected.

## [0.17.0] — unreleased

### Added

- **Hover text on the top-bar buttons.** Two of them differ only in how much
  they throw away, and a two-word label cannot carry that. `Tooltip` is drawn as
  a borderless toplevel that never takes focus.
- **A "Screenshot" button**, writing a PNG beside the interface's own files as
  `demo-<date>-<time>.png`. It captures the **content area only** — the top bar
  is iterlab's furniture and has no business in a figure someone pastes into a
  report. No file dialog: a modal blocks the test suite outright, the same
  reason element creation does not ask for a name. Pillow already ships with
  matplotlib, so this adds no dependency. A machine that cannot grab the screen
  (headless Linux) reports it through the fault banner rather than taking the
  window down.
- **A "More" drawer in the properties panel.** Only the tag, and the text for a
  button or label, are shown by default; position, size, colour, font and state
  are behind it. The set is declared per element type in
  `schema.BASIC_PROPERTIES`, so a future slider declares its range and starting
  position the same way a button declares its caption.

  The advanced widgets are *built* either way and only packed or not, so
  committing an edit never depends on which fields the researcher happened to
  reveal. The drawer stays open across selections — someone adjusting colours
  across several elements should not have to reopen it each time.

### Changed

- **"Restart app" is now "Hard reset"**, in the top bar and in the startup
  notice.
- **Positions and sizes are rounded to two decimals on construction**, not only
  when saved. Hundredths of the window is finer than anyone can place by hand or
  see, and finer than that turns the layout file into digits whose diffs mean
  nothing. Rounding at construction means what is in memory is what is on disk,
  so a value never changes under a researcher between drawing it and reopening
  it.

  Validation still runs first, so a genuinely invalid rectangle is rejected
  rather than quietly rounded into an acceptable one. Only rounding's own
  artefacts are corrected: a sliver that would round away to nothing becomes the
  smallest real element, and an edge rounded past the window is given its
  position back rather than being shrunk.

  `DEFAULT_SIZE["button"]` moves from `0.035` to `0.04` high, since a default
  ought to be expressible on the grid it will be snapped to.

## [0.16.0] — unreleased

### Fixed

- **An edited `on_startup` was often not noticed at all.** Reported as "nothing
  happens", and there were two independent reasons, either of which was enough
  on its own:

  1. The check hung off the dispatcher's after-invoke hook, which fires only
     when a handler actually ran. Clicking an element you have not written code
     for — normal, and silent by design — never looked at the file. So the
     notice appeared only if you happened to click something that already had a
     handler.
  2. Nothing checked without an interaction at all. Saving the file and looking
     at the window did nothing, which is exactly when a researcher expects
     something to happen.

  The check now runs before *every* interaction whatever it goes on to do, and
  a 700 ms poll notices a save on its own. It reads the file rather than the
  loaded module — deliberately, since reloading on a timer would re-run
  module-level code uninvited, and since the module is only reloaded when an
  interaction reaches a handler that exists.

### Added

- **A "Re-run startup" button in the top bar**, as requested. Enabled only when
  startup has actually been edited, so the button is its own indicator: save the
  file, look up, and it has come alive. It runs the new startup over the session
  already in memory, so the data survives.

### Changed

- The notice's second action is now **Restart app**, the same restart the top
  bar offers, rather than a separate session-only restart. One restart concept
  in the interface rather than two whose difference is invisible.
- `ModuleLoader.generation`, added in 0.13.0, is gone. The staleness check is
  keyed to the file's own (mtime, size) instead, which is what let it work
  without loading anything — and an API with one caller that no longer needs it
  is better deleted than kept.

## [0.15.0] — unreleased

### Changed

- **`ev.<tag>` for a plot is now a real matplotlib `Axes`**, not an object that
  forwards to one. `AxesHandle` subclasses `Axes` and is registered as a
  matplotlib projection, which is the supported way to have a figure build a
  particular Axes subclass.

  The difference is invisible for `ev.ax_0.plot(...)`, which worked either way,
  and decisive everywhere else. `isinstance(ev.ax_0, Axes)` is now true, so any
  library that takes an `ax=` argument accepts it, and matplotlib's own
  machinery does too. A forwarding wrapper fails all of that — and fails it
  inside whatever library the researcher passed it to, a long way from anything
  iterlab wrote.

- **The element type `plot_area` is renamed `axes`**, and new ones are tagged
  `ax_0`, `ax_1`, … rather than `plot_0`. `ax` is what the variable is called in
  everyone's matplotlib code, so `ev.ax_0` reads the way a researcher's own code
  already does. What the layout calls the thing is now what the thing is.

- **Layout schema 2 → 3**, with a migration that rewrites `type: plot_area` to
  `type: axes`. Tags, positions and styles are untouched, so an interface drawn
  before this keeps working and keeps its names.

### Notes

- Everything iterlab adds to the Axes subclass is prefixed `_iterlab_`, except
  the deliberate public surface (`tag`, `visible`, `canvas`, `widget`,
  `element`, `disconnect`). A test asserts that nothing added shadows a
  matplotlib attribute, so a future matplotlib release cannot quietly collide
  with us.
- `visible` keeps its element-level meaning — is this on screen — uniform with
  buttons and labels, and hides the toolbar with it. matplotlib's own
  `set_visible` is left alone and still does matplotlib's thing.

## [0.14.0] — unreleased

### Added

- **A "Restart app" button in the top bar**, beside the mode toggle. A cold
  restart: the layout is re-read from disk, the researcher's module is dropped
  from the import cache, and a new session begins. It is the answer to anything
  a warm reload deliberately does not cover — an edited helper module, a
  hand-edited layout file, or simply wanting a clean slate.

  It stays in the mode it was pressed in. Restarting is not a request to be
  moved to a different screen, and the window is not resized either: that would
  rearrange the researcher's desktop, which is not what was asked for.

  Replaces the narrower "Restart session" button in the top bar. That behaviour
  still exists and is still offered by the startup notice, where re-running
  startup over a live session is the point; as a top-bar control, one button
  with one meaning beats two whose difference is invisible until it bites.

### Fixed

- A layout file edited by hand into something unparsable took the window down on
  restart, which is precisely what Principle III forbids. The last good layout
  is kept, the interface carries on, and the error is reported through the
  banner rather than swallowed. Found by a test written to check something else,
  which crashed instead of failing.

## [0.13.0] — unreleased

### Added

- **An edited `on_startup` is now noticed and offered back.** Every other
  handler takes effect on the next click because the next click runs it;
  startup already ran, so editing it did nothing at all and nothing said so.
  Nothing raises, so no fault appeared — the code simply never ran, which is
  the most expensive silence this tool can produce.

  A strip now appears offering **Re-run startup** (keeps `ev` and everything on
  it) and **Restart session** (discards it). Both are offered rather than one
  chosen, because whether re-running is safe depends on the researcher's code:
  `ev.x = load(...)` rebinds and is safe, `ev.log.append(...)` is not. Dismissing
  hides the strip without marking the edit accepted, so a further edit raises it
  again — ignoring one edit must not make the next one silent.

- `runtime/startupcheck.py`. What counts as "startup changed" is narrower than
  "the file changed" — otherwise every handler edit would cry wolf — and wider
  than "the text of `on_startup` changed", because startup's behaviour lives
  partly in the module-level helpers it calls. The fingerprint covers
  `on_startup` plus every module-level function transitively reachable from it,
  compared as parsed structure so reformatting and comments cost nothing. A
  file mid-edit that will not parse fingerprints as `None` and raises no alarm.

- `ModuleLoader.generation`, so a caller can ask "has this reloaded since I last
  looked?" without re-reading the file. The staleness check is therefore
  proportional to edits, not to clicks.

### Notes

- **New imports already worked** and needed no change: the loader executes the
  module fresh rather than calling `importlib.reload`, so an `import` line added
  to a live file runs on the next reload. Verified rather than assumed.
- **Imported modules are assumed not to change during a session.** If `demo.py`
  does `import fitting` and `fitting.py` is then edited, the change is not
  picked up: `fitting` is already in `sys.modules`, so the import statement
  binds the cached module. This is a deliberate scope boundary, not an
  oversight - cascading reloads through a module graph brings the stale-instance
  problem with it (objects already built keep their old class), and the cost of
  getting that subtly wrong is higher than the cost of restarting. **Restart
  app** covers it when it matters.

## [0.12.0] — unreleased

### Changed

- **A session now survives a mode switch.** It belongs to the interface, not to
  GUI mode. Toggling into the editor to nudge a button and back no longer
  discards `ev`, no longer blanks a plot, and no longer re-runs `on_startup`.

  This reverses FR-015d, which said a switch ends the session. That behaviour
  did not remove the cost of reloading data so much as move it: from "every
  code edit", which the reload loop already solved, to "every layout edit",
  which is the other half of the same loop. A researcher with a slow load was
  still paying it, just for a different reason.

### Added

- **A "Restart session" control** beside the mode toggle. Because toggling now
  preserves everything deliberately, there has to be one explicit way to say
  start over — and it is how a change to `on_startup` takes effect. Chrome
  under FR-015c, and disabled in editor mode, where there is no live session to
  discard (FR-015e).
- `Session`, owning what outlives a mode: `ev`, one matplotlib `Figure` per plot
  area, and whether startup has run. A `Figure` can be attached to a new canvas,
  which is what makes a drawn plot survive at all.
- `Session.reconcile` and `Session.retag`, so state belonging to an element
  deleted in the editor is dropped and state belonging to a renamed one follows
  the new tag (FR-015f).

### Fixed

- A figure's callback registry is shared with **every canvas it is ever attached
  to**. Reusing the figure across a switch therefore left the dead canvas's
  connections live, so a single click fired the handler once per switch ever
  made — three toggles, four handler calls. `PlotHandle.disconnect()` releases
  them on teardown. Found by prototyping before designing, and now covered by a
  test that fails with `assert 4 == 1` without the fix.

### Tests

- Three tests driving real matplotlib events through the canvas: a drawn curve
  survives a switch, a click fires exactly once after three switches, and a
  renamed plot keeps its curve. Each was confirmed to fail against the
  unfixed code.

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
