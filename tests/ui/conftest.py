"""Tk lifecycle for the display-dependent tier.

One root for the whole session. Windows Tk does not survive dozens of
create/destroy cycles in a single process — it fails later with an
unrelated-looking "invalid command name" error — so tests share a root and
clean up their own widgets instead.
"""

import pytest


@pytest.fixture(scope="session")
def tk_root():
    import tkinter

    root = tkinter.Tk()
    root.withdraw()  # never actually shown; tests drive it directly
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def make_app(tk_root, tmp_path, monkeypatch):
    """Open an interface against the shared root, and clean up after."""
    from iterlab.app import open_interface

    monkeypatch.chdir(tmp_path)
    created = []

    def _make(name="demo"):
        app = open_interface(name, _show=False, _root=tk_root)
        created.append(app)
        return app

    yield _make

    for app in reversed(created):
        try:
            app.close()
        except Exception:
            pass
    for child in tk_root.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass
