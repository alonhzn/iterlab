# Manual Verification — Release Gate 2

The project constitution (Principle VII, NON-NEGOTIABLE) defines two release gates. **Gate 1** is the
automated suite. **Gate 2** is this document.

## The rules that keep this honest

1. **Only what cannot be automated belongs here.** Anything on this list that a machine could assert is
   a gap in Gate 1, and belongs there instead.
2. **A pass that was not recorded did not happen.** Publishing without a row in the results table below
   is a defect in the process, not a technicality.
3. **This list is expected to shrink.** It must not grow to absorb work that was merely easier by hand.

No version is published to PyPI unless both gates pass. No "small fix" exemption, no "docs only"
exemption, no override of either gate.

---

## How to do a pass

```console
python tools/verify.py
```

That builds a throwaway interface — a plot, a label and two buttons — with research code that
loads slowly, plots, and fails on demand, then opens it. Everything is in a temporary directory and
is deleted when you close the window, so none of your own work is touched. Keep this file open
beside it.

Budget about ten minutes. When you are done, add a row to *Recorded results* and say what you
found. **A pass that was not recorded did not happen** — that is the rule that stops this decaying
into "we looked at it once".

## Checklist

Every item is here because a machine can confirm the mechanism but not the *experience*. Items
marked **[!]** are the ones most likely to be wrong and least likely to be caught by Gate 1.

### Look and layout

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 1 | Toggle to GUI mode | The arrangement matches what you drew, with nothing overlapping or clipped | Tests assert coordinates; they cannot judge whether it *looks* like the sketch |
| 2 | Resize the window from small to full screen and back | Elements stay proportional; button labels and axis text stay readable at both extremes | `relwidth` is asserted automatically; legibility is a human judgement |
| 3 | Look at the top-left toggle in both modes | It is obvious, reads as a mode switch, and is never hidden behind an element | Presence is tested; whether it reads as a control is not |
| 4 | Open the editor with nothing drawn | The palette makes it obvious what can be added and how | Discoverability cannot be asserted |

### Responsiveness

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 5 | Click the toggle repeatedly | Switching feels instant, with no visible flicker or relayout | A timing budget is testable; "feels instant" is not |
| 6 | **[!]** Click **Redraw** ten times, then edit the `2` in `on_clicked_redraw` to `5`, save, and click again | The curve changes; the 1.5-second load does **not** repeat. This is the paradigm's whole claim | Reload counts are tested; whether the loop *feels* immediate is not |
| 7 | **[!]** Add elements until there are ~20, and interact | No perceptible slowdown as they accumulate | This is the regression that killed the 2024 spike; the automated test uses a threshold, the human check is whether it *feels* slow |
| 8 | Drag an element around the canvas | Dragging tracks the pointer without lag or jumping | Smoothness is not assertable |

### The session surviving

Added at 0.12.0, when a mode switch stopped ending the session. The automated tests prove the state
is *there*; only a person can see that the window still looks like the session they left.

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 18 | **[!]** Draw a plot, let the 1.5-second load run, then toggle to the editor, move a button, and toggle back | The curve is still on screen and the load does **not** repeat. Rearranging a live interface costs nothing | Line counts are asserted; whether the plot *looks* untouched — same zoom, same axes, no flash of blank canvas — is not |
| 22 | Edit `on_startup`, then click any element | The strip appears, and its two actions read as clearly different from each other | Visibility is asserted; whether a researcher can tell "re-run" from "restart" at a glance is not |
| 23 | Press **Re-run startup** with data already loaded | The edit applies and the data is still there | The object identity is asserted; whether the researcher *believes* nothing was lost is not |
| 25 | Hover each top-bar button, then look at **Hard reset** without pressing it | The text appears without chasing the pointer, reading it makes clear which one costs you your data, and **Hard reset** reads as destructive *before* it is pressed | Presence is asserted; whether it arrives before you have moved on, and whether the danger is legible, are human judgements |
| 28 | Draw an element, then look at PROPERTIES | The two fields that matter are there and the rest is out of the way; **More** reads as openable | Whether a panel feels uncluttered is exactly what a machine cannot say |
| 30 | Drag an element slowly across the canvas | Movement is smooth, not visibly stepped, despite positions snapping to hundredths | One part in a hundred should be below the threshold of notice. If stepping is visible, the grid is too coarse |
| 32 | **[!]** Type into a text box, click a button that changes a label, then toggle to the editor and back | Everything is exactly as you left it - the typed text, the changed label, any colour your code set | Asserted now, but this shipped broken and was found by hand. Worth confirming it *feels* like the same session rather than a reset one |
| 34 | **[!]** Draw a file selector and click it | Your operating system's real file chooser opens, looks native, and is not behind the window | Every automated test replaces this dialog, because a suite that waits for a human is not a gate. Nothing but a person has ever seen the real one open |
| 35 | **[!]** Set **Types** to `txt, csv`, then open the chooser | Only those files are offered, and "All files" is still available in the dropdown | The filter reaching Tk is asserted; whether the OS honours it, and whether the escape hatch is findable, is not |
| 39 | **[!]** Draw a number box and an axes, wire the box's handler to redraw the plot, then type a value and press Enter | Nothing happens while typing; the plot redraws once, on Enter | The counts are asserted. What a person is checking is that waiting for Enter feels right rather than unresponsive - if it feels broken, the trade is wrong |
| 41 | Draw several elements, then open `demo.py` | The `if __name__` block is still at the bottom, with the new handlers above it and one blank line's worth of ordinary spacing | Ordering is asserted; whether the file still reads as something a person wrote is not |
| 42 | Type into a property field, then click straight onto another element | The value is saved. Repeat a few times with different fields | This broke twice in two releases, in different ways, and both times the automated check passed while a person could see it fail |
| 60 | **[!]** Right-click an element in the editor and choose its handler, once from VS Code and once from PyCharm if you have both, and once with the other one picked in the heading | Your editor comes to the front with the cursor on the handler's `def` line, in the window you already had open rather than a new one | Tests check the command each editor is sent. Whether that editor honours it, raises its window, and reuses the open project is up to the editor, and only visible on screen |
| 39a | Type in the box, then click straight onto another element without pressing Enter | The handler runs once, on the way out | Focus-loss commit is asserted through a synthesised event; only a person can confirm a real click out of the box does it |
| 39b | Click into a box, change nothing, click away | Nothing runs | The rule that keeps a plot from redrawing when someone merely clicks past |
| 43 | **[!]** In the editor, move the pointer across several elements without stopping | Tags appear only where you pause, not as a trail of boxes flickering past | The delay is asserted as a number; whether 200 ms *feels* like an answer rather than a flicker or a wait is the only thing that matters and cannot be measured |
| 45 | Clear a label's text in the editor, then switch to GUI mode | The label is blank there, and still shows its tag on the editor canvas | Both halves are asserted. A person is checking that an invisible element is still workable in the editor |
| 46 | **[!]** Lay out a handful of elements the way you actually would | Picking a type each time reads as deliberate rather than tedious. If it feels like one click too many, the trade is wrong | The counts are asserted. Whether a two-step add is worth it over an accidental element now and then can only be judged by doing it |
| 49 | Switch to GUI mode with a label on a coloured background | The label reads as text on that background, with no box and no edge around it | Asserted as a colour match; whether it *looks* like part of the interface is the point |
| 54 | **[!]** Draw a square element, then switch to GUI mode | It is still square. Repeat at a few window sizes | The canvas's proportions are asserted to match the interface; whether the layout *looks* like what you drew is the reason for the whole change |
| 56 | Fold and unfold the toolbar a few times with elements on the canvas | The window never moves; the canvas grows into the freed room at the same proportions, and shrinks back | Asserted, but a canvas that twitches on every fold would make the feature unusable |
| 57 | Fold the toolbar on a small interface, then try to edit an element | It is workable: press Toolbar, edit, fold again | The reason folding exists. If it is awkward, a small interface is still hard to edit and the design needs revisiting |
| 58 | **[!]** Make the interface short and wide - say 800x260 - and open the editor | The canvas keeps the interface's proportions, centred, and the grey around it reads as the editor's margin, not as a broken or half-drawn canvas | The proportions are asserted. Whether the grey reads as deliberate is the judgement the scaled canvas rests on |
| 59 | **[!]** Write real code against an element, then rename it and read the whole file | It still reads like something you wrote: nothing reflowed, no line you did not expect has moved, and every mention that moved should have | The mechanics are asserted exhaustively. Whether your file still feels like yours after iterlab has edited it is the judgement this whole exception to Principle V rests on |

### Being told things

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 9 | **[!]** Click **Break it**, while looking at the plot rather than the terminal. Then fix the error and click again | The banner catches your eye without you hunting for it, and clears the moment the fix is in | Tests assert that the banner shows and clears; whether it is *noticeable*, and whether the recovery feels immediate, is the whole point |
| 10 | **[!]** Draw one more button, write nothing for it, click it | Nothing happens, nothing is reported, and this reads as *intended* rather than broken | Silence is tested; whether it reads as intentional is not |
| 12 | Read a fault message without looking at the terminal | It tells you which element failed and roughly what went wrong | Message content is tested; usefulness is not |

### First contact

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 13 | **[!]** Hand the tool to someone who has never seen it, with only the command | They produce a window with a working button inside two minutes, unaided | SC-001 is a human-factors claim by construction. The only item here needing a second person; skip it on a routine pass and do it before any release that goes near other people |
| 14 | Read the generated starter file as a newcomer | The comment about loading data in `on_startup` is clear enough to actually follow | Presence of the text is tested; persuasiveness is not |

### Platform

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 15 | Run on Windows, macOS and Linux | Fonts, spacing and the toolbar look right on each | CI asserts it runs; nobody sees the result |
| 16 | On a Linux box without `python3-tk` | Exit code 3, with a message naming tkinter and the install command | The message is tested; whether a stuck researcher can act on it is not |
| 17 | Hover each resize handle in editor mode, on each platform you ship to | The pointer changes, and the corner cursors differ from the edge ones | Tk silently ignores a cursor name it does not know. CI now checks the names are *valid*; only a person can see whether the right one appears |

### Retired to Gate 1

Numbers are never reused, so a recorded pass keeps meaning what it said. Each of these is now
asserted by the automated suite, and rule 1 above says that is where it belongs.

| # | Was | Now asserted by |
|---|---|---|
| 11 | The banner clears after a fix | Merged into 9 |
| 19 | Whether a pan or zoom survives a trip to the editor | Decided 2026-09-26 that it should: `test_toolbar.py`, the view and the history Home and Back walk |
| 20 | One click fires once after several toggles | `test_plot_events.py::test_a_click_fires_once_however_many_switches` |
| 21 | Hard reset reads as destructive | Merged into 25 |
| 24 | An edited helper module is picked up by Hard reset | `test_restart_app.py::test_it_picks_up_an_edited_helper_module`, through the real button |
| 26 | The Screenshot PNG is the interface, at its size, with no top bar | `test_screenshot.py`, against a real screen grab: size, and an element's edges to the pixel |
| 27 | The Screenshot PNG shows a mid-zoom plot as zoomed | `test_screenshot.py::test_the_picture_shows_the_zoom_on_screen` |
| 29 | The drawer stays open across selections | `test_properties_drawer.py::test_it_stays_open_when_another_element_is_selected` |
| 31 | The title bar shows the mark, not a placeholder | `test_icon.py::test_the_title_bar_shows_the_mark`, on Windows, by grabbing the title bar |
| 33 | An editor caption edit beats the remembered one | `test_presentation_survives.py::test_editing_the_caption_in_the_editor_beats_the_remembered_one` |
| 36 | A chosen file survives closing iterlab | `test_real_launch.py`, across two real processes |
| 37 | A deleted file reads as empty and opens where it was | `test_real_launch.py`, across two real processes |
| 38 | A moved project starts over quietly | `test_real_launch.py`, across two real processes |
| 40 | The IDE's run button opens the interface | `test_real_launch.py::test_running_the_file_opens_the_interface`: `python demo.py`, from another directory |
| 44 | The tag disappears during a drag | `test_tag_tooltip.py::test_dragging_does_not_leave_it_hanging` |
| 47 | Clicking the empty canvas creates nothing | `test_arming.py::test_clicking_the_canvas_creates_nothing` and the background-click tests beside it |
| 48 | A label and both selectors can be told apart | `test_element_colours.py`: perceptual colour distance between every pair of types, checked against the pair that shipped broken |
| 50 | The size survives a real close and relaunch | `test_real_launch.py`, across real processes |
| 51 | A size set in the editor survives a relaunch | `test_real_launch.py::test_a_resized_editor_reopens_the_interface_that_size` |
| 52 | A real downgrade backs both files up | The `downgrade` CI job: a project made by this version, opened by the previous release from PyPI |
| 53 | The 1.x notice | `test_style.py::test_opening_a_1x_project_says_what_happened`. 1.x had no users to meet it |
| 55 | No drift between modes over several rounds | `test_look.py::test_resizing_in_either_mode_does_not_drift_over_several_rounds`, and the relaunch drift test |

---

## Confirmed so far

Items checked outside a full release pass. Useful because it shows what has actually been looked
at, and at which version — a confirmation against an old build is worth less than a fresh one.
This is **not** a substitute for a release pass: a release needs the whole list worked through and
a row in the table below.

| # | Item | Confirmed | Version | Note |
|---|---|---|---|---|
| 9 | **[!]** The fault banner is noticeable while looking at the plot | 2026-09-08 | 0.7.0 | Confirmed visible |

---

## Recorded results

One row per release. An empty table means nothing has been released.

| Version | Date | Platform | Outcome | Defects found |
|---|---|---|---|---|
| 0.1.0-dev | 2026-09-07 | Windows 11 | Not a release — development walkthrough only | 1 (see below) |
| 1.4.0 | 2026-09-11 | Windows 11 | Pass — reported by the maintainer | 0 |
| 1.5.0 | 2026-09-12 | Windows 11 | Pass — reported by the maintainer | 0 |
| 1.6.0 | 2026-09-13 | Windows 11 | Pass — reported by the maintainer | 0 |
| 2.0.0 | 2026-09-14 | Windows 11 | Pass — reported by the maintainer | 0 |
| 2.0.1 | 2026-09-14 | Windows 11 | Pass — reported by the maintainer, recorded 2026-09-26 | 0 |
| 2.1.0 | 2026-09-26 | Windows 11 | Pass — reported by the maintainer | 0 in the pass; 3 found by hand before it (see below) |

### 2026-09-07 — development walkthrough

Not a release pass; the checklist above has not been worked through on a real
display, and no version has been published. Recorded because it found a defect.

Walking `specs/001-end-to-end-loop/quickstart.md` step 7 against the real
application surfaced a bug the automated suite had missed: adding an element to
an interface whose `.py` used CRLF line endings rewrote **every line** in the
file. `Path.read_text` normalizes CRLF to LF in memory, and writing that back
reflowed the whole file — a whole-file diff caused by adding one stub, which
FR-014 forbids.

Fixed by reading and writing the researcher's file with newline translation
disabled, and matching the file's own line endings when appending. Two
regression tests now cover it, so this belongs to Gate 1 from here on and is
deliberately **not** added to the checklist above.
### 2026-09-11 — 1.4.0

The first recorded release pass. `tools/verify.py` had been raising `TypeError`
on its first element since `create_element`'s `name` argument became `tag`, so
until this release the pass could not be started at all — which is why every
row above this one is absent. Fixed, and the suite now runs the tool.

Worked through on Windows 11 by the maintainer, who reported everything
working. Nothing recorded as found.

### 2026-09-12 — 1.5.0

Worked through on Windows 11 by the maintainer, who reported everything
working. Nothing recorded as found.

### 2026-09-13 — 1.6.0

The release where Gate 2 carried the most weight so far: the editor canvas
became a scaled picture of the run window rather than the window itself, the
backdrop behind it is new, folding the toolbar does something different, and a
new project opens at half the screen. Counting pixels and renders cannot say
whether any of that is comfortable to draw on.

Worked through on Windows 11 by the maintainer, who reported it passing.
Nothing recorded as found.

### 2026-09-14 — 2.0.0

The file every project depends on changed shape: the layout left YAML for
`demo_layout.py`, which now carries the `Ev` class as well. Files written by
1.x do not open, deliberately and with no migration.

Worked through on Windows 11 by the maintainer, who reported it passing.
Nothing recorded as found.

1.7.0 was the last version published. 1.7.1 was prepared and gated but
overtaken before upload; its changes ship here.

### 2026-09-14 — 2.0.1

The starter code file gained its boilerplate frame. Worked through by the
maintainer before upload and reported passing, but the row was not written at
the time: it was added on 2026-09-26, on the maintainer's report, when the gap
was noticed while preparing 2.1.0. Recorded late rather than left looking as
though the pass never happened.

### 2026-09-26 — 2.1.0

The first pass against the shortened list: 59 items became 37, with eleven
moved into Gate 1 as real launches, real screenshots and a real downgrade, and
one new item (60) for the right-click menu that opens a handler in your
editor. The maintainer had already seen that menu reach the right line in VS
Code before the pass.

Worked through on Windows 11 by the maintainer, who reported it passing.
Nothing recorded as found in the pass itself.

Found by hand during this release's development, and each fixed with a Gate 1
test before the pass:

- A plot's toolbar left in zoom mode kept answering drags after a trip to the
  editor, raising `invalid command name ...canvas` on each one. The test that
  first covered zoom surviving the trip never pressed the zoom tool.
- `on_key_` never fired on a button: none of button, selector or label takes
  the keyboard when clicked. It is now offered only where it can fire.
- The first switch to the interface paused while matplotlib imported. It now
  imports while the window opens.
