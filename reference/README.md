# reference/ — read-only legacy

Everything under this directory is **historical reference material**. It is not part of iterlab.

- `legacy-rrGUI/` — the 2024 spike, copied verbatim from `C:\Users\alonh\rrGUI`.
  Never imported, never executed, never modified. It is not on the import path and has no bearing
  on the build.
  **Not tracked in git** (see the repository `.gitignore`) — it exists only in the author's working
  copy. Line-number citations in `LEARNINGS.md` refer to it and cannot be followed from a clone.
- `LEARNINGS.md` — the distillation, and the only tracked content here.
  **This is the only file the Spec Kit workflow should read.**

Porting any code out of `legacy-rrGUI/` requires an explicit task in `tasks.md` that names the source
file and lines.
