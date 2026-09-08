"""Shared test fixtures.

matplotlib is forced to a non-interactive backend before anything imports it,
so the headless tier of the suite never tries to open a window.
"""

import matplotlib

matplotlib.use("Agg", force=True)

import pytest  # noqa: E402  (must follow the backend selection)


@pytest.fixture
def tmp_interface(tmp_path):
    """A temporary directory plus the (name, layout_path, code_path) triple.

    Neither file is created; tests that want them create them explicitly, so
    that "the file does not exist yet" stays a testable state.
    """

    class Interface:
        def __init__(self, directory, name="demo"):
            self.dir = directory
            self.name = name
            self.layout_path = directory / f"{name}.yaml"
            self.code_path = directory / f"{name}.py"

        def write_code(self, text):
            self.code_path.write_text(text, encoding="utf-8")
            return self.code_path

        def write_layout(self, text):
            self.layout_path.write_text(text, encoding="utf-8")
            return self.layout_path

    return Interface(tmp_path)


@pytest.fixture(autouse=True)
def no_blocking_dialogs(monkeypatch):
    """Make any modal dialog fail loudly instead of waiting for a human.

    A test suite that stops for a dialog is not an automated release gate
    (constitution Principle VII, Gate 1). Without this, one code path that
    opens a modal turns the whole suite into a manual procedure, and the
    failure looks like a hang rather than a defect.
    """
    import tkinter.filedialog
    import tkinter.messagebox
    import tkinter.simpledialog

    def refuse(name):
        def _refuse(*args, **kwargs):
            raise AssertionError(
                f"{name} tried to open a modal dialog during a test. "
                f"Tests must never wait for a human; either avoid the dialog "
                f"or drive it explicitly."
            )
        return _refuse

    for module, names in (
        (tkinter.simpledialog, ("askstring", "askinteger", "askfloat")),
        (tkinter.messagebox, ("showinfo", "showwarning", "showerror",
                              "askyesno", "askokcancel", "askretrycancel")),
        (tkinter.filedialog, ("askopenfilename", "asksaveasfilename",
                              "askdirectory")),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, refuse(f"{module.__name__}.{name}"))
