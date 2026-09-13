"""Renaming an element: its handlers, and every reference to it.

**This is the only module in iterlab permitted to modify a line the researcher
wrote** (constitution Principle V), so what it will and will not touch is worth
stating exactly.

It renames:

  * the element's handlers, `on_<interaction>_<tag>`,
  * attribute access on it - `ev.old`, and `anything.old`,
  * whole-word mentions in comments,
  * whole-word mentions inside strings, which is also how `ev.old` written
    inside an f-string is reached.

It does not rename a *bare* identifier that merely shares the name. A local
called `old` is a coincidence of naming rather than a reference to the element,
and nothing here can tell the difference - so it is left alone, which is the
same conservatism that protects an unrelated element from a rename.

The rule that makes this safe is that a name is matched **whole or not at all**.
Renaming `cmdRun` must not touch `cmdRunAlgorithm`, which is a different element
that would be silently unwired; nor `on_clicked_cmdRunAlgorithm`; nor
`old_cache`. Text substitution of the old name would hit all three, which is why
the work is driven by the tokenizer and the parser rather than by `str.replace`.

Nothing is written unless the file parses. Without a parse there is no way to
tell a definition from an incidental mention, and guessing would put the
researcher's work at risk - which is what this exception to Principle V exists
to avoid, not to create.

No GUI imports.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

from ..errors import CodeFileUnparseable
from ..layout.schema import INTERACTIONS
from .templates import CRLF, LF, atomic_write, read_source

#: Token types whose text is prose rather than code, so a mention inside one is
#: renamed by whole word. FSTRING_MIDDLE exists from 3.12, where an f-string is
#: tokenized in pieces; before that the whole f-string arrives as one STRING and
#: this same rule covers both its text and its `{ev.old}` interpolations.
_PROSE = {tokenize.COMMENT, tokenize.STRING}
_FSTRING_MIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)
if _FSTRING_MIDDLE is not None:  # pragma: no branch - version dependent
    _PROSE.add(_FSTRING_MIDDLE)


@dataclass(frozen=True)
class Renamed:
    """What a rename actually changed, so the caller can say so."""

    handlers: tuple = ()
    #: `ev.old` and friends - attribute access on the element.
    references: int = 0
    #: Whole-word mentions in comments and strings.
    mentions: int = 0
    #
    # The split between the two moves with the Python version: from 3.12 an
    # f-string is tokenized in pieces, so `ev.old` inside one is a reference;
    # before that the whole f-string is a single string, so it is a mention.
    # The file comes out the same either way, which is what matters - do not
    # write a test against the split.

    def __bool__(self):
        return bool(self.handlers or self.references or self.mentions)

    @property
    def total(self) -> int:
        return len(self.handlers) + self.references + self.mentions


def handler_names_for(tag: str) -> set:
    """Every handler name that element could have, written or not."""
    return {f"on_{interaction}_{tag}" for interaction in INTERACTIONS}


def _renamed_handler(handler: str, old: str, new: str) -> str:
    # handler is known to be exactly on_<interaction>_<old>, so slicing off the
    # suffix is exact - no substring risk.
    return handler[: -len(old)] + new


def _word(old: str):
    """`old` as a whole word, never as part of a longer one.

    Word boundaries treat the underscore as a word character, which is what
    keeps `on_clicked_old` and `old_cache` out of it - handlers are renamed by
    their own rule, and a longer name belongs to something else.
    """
    return re.compile(r"\b" + re.escape(old) + r"\b")


def _span_edits(token, replaced, word, new):
    """Edits for one prose token, one row at a time.

    A triple-quoted string covers several lines, and each line keeps its own
    ending - so the replacement is applied per line rather than by swapping the
    whole token, which would have to carry line endings of its own and would
    quietly normalize a file with mixed ones.
    """
    start_row, start_col = token.start
    end_row, end_col = token.end
    if start_row == end_row:
        return [(start_row, start_col, end_col, replaced)]

    lines = token.string.splitlines()
    edits = []
    for offset, line in enumerate(lines):
        changed, count = word.subn(new, line)
        if not count:
            continue
        row = start_row + offset
        first = start_col if offset == 0 else 0
        last = end_col if offset == len(lines) - 1 else first + len(line)
        edits.append((row, first, last, changed))
    return edits


def _edits_for(source, old, new):
    """Every (row, start_col, end_col, text) to apply, and a tally of each kind.

    Rows are 1-based, as the tokenizer reports them.
    """
    word = _word(old)
    handlers = handler_names_for(old)
    edits = []
    found_handlers = []
    references = 0
    mentions = 0

    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    for index, token in enumerate(tokens):
        if token.type == tokenize.NAME:
            previous = tokens[index - 1] if index else None
            after_dot = (
                previous is not None
                and previous.type == tokenize.OP
                and previous.string == "."
            )
            if token.string == old and after_dot:
                # `ev.old`, `self.old`, `handles.old` - a reference to the
                # element, whatever is on the left of the dot.
                edits.append((token.start[0], token.start[1], token.end[1], new))
                references += 1
            elif token.string in handlers:
                renamed = _renamed_handler(token.string, old, new)
                edits.append((token.start[0], token.start[1], token.end[1], renamed))
                found_handlers.append(token.string)
        elif token.type in _PROSE:
            replaced, count = word.subn(new, token.string)
            if count:
                edits.extend(_span_edits(token, replaced, word, new))
                mentions += count

    return edits, tuple(found_handlers), references, mentions


def rename_tag(code_path, old, new) -> Renamed:
    """Rename an element throughout the researcher's file. Returns what changed.

    Raises `CodeFileUnparseable` and writes nothing if the file will not parse.
    """
    path = Path(code_path)
    if not path.exists() or old == new:
        return Renamed()

    source = read_source(path)
    flat = source.replace(CRLF, LF)
    try:
        # Parsed for the guarantee, not for the edits: a file that does not
        # parse is one where "is this a mention or a definition" has no answer.
        ast.parse(flat)
        edits, handlers, references, mentions = _edits_for(flat, old, new)
    except (SyntaxError, tokenize.TokenError) as exc:
        raise CodeFileUnparseable(
            f"{path} could not be parsed, so renaming would not be safe: {exc}"
        ) from exc

    if not edits:
        return Renamed()

    lines = source.splitlines(keepends=True)
    # Last edit first, so an earlier one's columns are still true when it runs.
    for row, start, end, text in sorted(edits, reverse=True):
        line = lines[row - 1]
        lines[row - 1] = line[:start] + text + line[end:]

    atomic_write(path, "".join(lines))
    return Renamed(handlers=handlers, references=references, mentions=mentions)
