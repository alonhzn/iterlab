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
| 19 | Pan and zoom a plot, then toggle out and back | Whatever a person judges reasonable here, recorded either way. The figure survives; the toolbar's view stack may not | Nobody has decided yet whether the zoom *should* survive. This item exists to find out by looking |
| 20 | **[!]** After several toggles, click a plot once and watch the terminal | Exactly one line is printed | The duplicate-firing defect this feature nearly shipped. A test now catches it, but it is worth a human eye — it is invisible unless you are counting |
| 21 | Press **Restart app** | Everything reloads: data, plots, code, layout. It is obvious that is what happened | Whether the button reads as destructive *before* it is pressed is a human judgement |
| 22 | Edit `on_startup`, then click any element | The strip appears, and its two actions read as clearly different from each other | Visibility is asserted; whether a researcher can tell "re-run" from "restart" at a glance is not |
| 23 | Press **Re-run startup** with data already loaded | The edit applies and the data is still there | The object identity is asserted; whether the researcher *believes* nothing was lost is not |
| 24 | Edit a helper module you import, then press **Hard reset** | The change takes effect. Without the restart it does not | A documented assumption. Worth confirming a researcher can discover the workaround from the guide |
| 25 | Hover each top-bar button | The text appears without chasing the pointer, and reading it makes clear which one costs you your data | Presence is asserted; whether it arrives before you have moved on is a human judgement |
| 26 | **[!]** Press **Screenshot**, then open the PNG | It shows your interface, at the size on screen, with no top bar and nothing clipped | The capture is faked in tests, because a screen grab needs a screen. Only a person can look at the picture |
| 27 | Press **Screenshot** with a plot mid-zoom | The PNG shows the zoom you were looking at | The point of a screen grab over a redraw, and only visible by looking |
| 28 | Draw an element, then look at PROPERTIES | The two fields that matter are there and the rest is out of the way; **More** reads as openable | Whether a panel feels uncluttered is exactly what a machine cannot say |
| 29 | Open **More**, select a different element | The drawer is still open | Asserted, but worth feeling: this is the difference between the drawer helping and annoying |
| 30 | Drag an element slowly across the canvas | Movement is smooth, not visibly stepped, despite positions snapping to hundredths | One part in a hundred should be below the threshold of notice. If stepping is visible, the grid is too coarse |
| 31 | **[!]** Open an interface and look at the title bar and taskbar | The iterlab mark is there, and is the mark - not a blank square or a generic placeholder | Tk reports success for an icon that renders as an empty grey box. Only a person looking at the title bar can tell the difference, which is how this shipped broken once |
| 32 | **[!]** Type into a text box, click a button that changes a label, then toggle to the editor and back | Everything is exactly as you left it - the typed text, the changed label, any colour your code set | Asserted now, but this shipped broken and was found by hand. Worth confirming it *feels* like the same session rather than a reset one |
| 33 | Change a button's caption in the editor, then return to GUI mode | The new caption is there, not the one the code had set | The rule that makes item 32 safe: an explicit edit beats a remembered value |
| 34 | **[!]** Draw a file selector and click it | Your operating system's real file chooser opens, looks native, and is not behind the window | Every automated test replaces this dialog, because a suite that waits for a human is not a gate. Nothing but a person has ever seen the real one open |
| 35 | **[!]** Set **Types** to `txt, csv`, then open the chooser | Only those files are offered, and "All files" is still available in the dropdown | The filter reaching Tk is asserted; whether the OS honours it, and whether the escape hatch is findable, is not |
| 36 | **[!]** Pick a file, close iterlab completely, reopen and click the selector | It opens where you left off, and `ev.fileselect.path` already holds the choice | The point of storing it outside the process. Asserted against a fake dialog; worth seeing survive a genuine restart |
| 37 | Pick a file, delete it outside iterlab, then look at the interface | `.path` reads as empty and the chooser opens in the folder it was in | The fallback only matters when it happens to a real file on a real disk |
| 38 | Move the whole project folder somewhere else and open it | The remembered selection is gone and it behaves like a first run - no error, no stale path | A documented consequence of keeping the memory out of the project. Worth confirming it is uneventful rather than confusing |
| 39 | **[!]** Draw a number box and an axes, wire the box's handler to redraw the plot, then type a value | The plot follows the digits as they are typed, without stutter | The handler firing is asserted; whether following a value *feels* immediate rather than laggy is the whole point and only a person can judge it |
| 40 | **[!]** Press your IDE's run button on `demo.py` | The interface opens, exactly as `iterlab demo` would | Tests execute the guard with `run` replaced, so no test has ever watched a real IDE launch a real window |
| 41 | Draw several elements, then open `demo.py` | The `if __name__` block is still at the bottom, with the new handlers above it and one blank line's worth of ordinary spacing | Ordering is asserted; whether the file still reads as something a person wrote is not |
| 42 | Type into a property field, then click straight onto another element | The value is saved. Repeat a few times with different fields | This broke twice in two releases, in different ways, and both times the automated check passed while a person could see it fail |

### Being told things

| # | What to do | Pass means | Why a machine cannot say |
|---|---|---|---|
| 9 | **[!]** Click **Break it**, while looking at the plot rather than the terminal | The banner catches your eye without you hunting for it | Tests assert `banner.visible`; whether it is *noticeable* is the whole point |
| 10 | **[!]** Draw one more button, write nothing for it, click it | Nothing happens, nothing is reported, and this reads as *intended* rather than broken | Silence is tested; whether it reads as intentional is not |
| 11 | Fix the error and click again | The banner clears and the recovery feels immediate | State is tested; the felt experience is not |
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
