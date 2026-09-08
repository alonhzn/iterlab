"""Exception types shared across layers.

These describe faults in *inputs* — a malformed layout, an unusable name, a code
file that will not parse. They are deliberately separate from `runtime.faults`,
which describes faults in the *researcher's code* and must never terminate the
process (constitution Principle III).
"""


class IterlabError(Exception):
    """Base for every error iterlab raises deliberately."""


class LayoutInvalid(IterlabError):
    """A layout file could not be understood.

    Reported with what is wrong. The file is never silently discarded or
    overwritten (FR-036).
    """


class LayoutVersionTooNew(IterlabError):
    """A layout was written by a newer iterlab than this one.

    The file is not opened, not partially interpreted, and above all not written
    back — saving it would discard whatever the newer version recorded (FR-036b).
    """

    def __init__(self, found: int, supported: int, path=None):
        self.found = found
        self.supported = supported
        self.path = path
        where = f" ({path})" if path else ""
        super().__init__(
            f"This layout{where} was written by a newer version of iterlab "
            f"(layout schema {found}; this build understands {supported}). "
            f"Upgrade iterlab to open it. The file has not been modified."
        )


class NameInvalid(IterlabError):
    """An element name could not be used in Python code.

    Caught at the point of entry rather than at generation time, so the failure
    surfaces where the cause is (FR-005b).
    """


class NameInUse(IterlabError):
    """Another element in this interface already has that name (FR-005e)."""


class CodeFileUnparseable(IterlabError):
    """The researcher's code file will not parse.

    Blocks stub insertion and renaming, both of which need an AST to act
    safely. Never a reason to end a session — only a reason to refuse a
    particular edit (R6, R14).
    """
