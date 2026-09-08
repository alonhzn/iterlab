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
