"""The offer to re-run a `on_startup` that has been edited.

Every other handler takes effect on the next click, because the next click is
what runs it. `on_startup` is the exception: it ran once, when the session
began, so editing it does nothing at all until something re-runs it. Nothing
raises, so no fault appears — the code just never runs, which is the most
expensive kind of silence this project can produce.

This is the same shape as the fault banner and behaves the same way: a strip in
the window, never a dialog, so the researcher can ignore it and carry on
(FR-033a). It differs in carrying an action, because unlike a fault there is
something iterlab can do about this on request.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BACKGROUND = "#fff8e1"
FOREGROUND = "#7a5300"

MESSAGE = "on_startup has changed since it last ran."


class StartupNotice:
    """Tells the researcher startup is stale, and offers to re-run it."""

    def __init__(self, parent, on_rerun, on_restart=None):
        self.frame = tk.Frame(parent, bg=BACKGROUND)
        self.label = tk.Label(
            self.frame,
            text="",
            bg=BACKGROUND,
            fg=FOREGROUND,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.label.pack(side="left", fill="x", expand=True, padx=8, pady=4)

        # Dismiss sits furthest right, away from the two actions, so the button
        # that does nothing is not adjacent to the one that discards data.
        self.dismiss_button = ttk.Button(
            self.frame, text="Dismiss", width=9, command=self.dismiss
        )
        self.dismiss_button.pack(side="right", padx=(2, 8), pady=4)

        if on_restart is not None:
            self.restart_button = ttk.Button(
                self.frame, text="Restart app", command=on_restart
            )
            self.restart_button.pack(side="right", padx=2, pady=4)
        else:
            self.restart_button = None

        self.rerun_button = ttk.Button(
            self.frame, text="Re-run startup", command=on_rerun
        )
        self.rerun_button.pack(side="right", padx=2, pady=4)

        self.visible = False

    # -- state -----------------------------------------------------------

    def show(self) -> None:
        self.label.configure(text=f"↻  {MESSAGE}  Re-running keeps your data.")
        if not self.visible:
            self.frame.pack(side="bottom", fill="x")
            self.visible = True

    def dismiss(self) -> None:
        """Hide it without re-running.

        Dismissing is not the same as accepting: the session's record of what
        startup looked like is left alone, so a *further* edit raises the notice
        again. Choosing to ignore this edit must not make the next one silent.
        """
        self._hide()

    def _hide(self):
        if self.visible:
            self.frame.pack_forget()
            self.visible = False

    @property
    def text(self) -> str:
        return self.label.cget("text")
