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
