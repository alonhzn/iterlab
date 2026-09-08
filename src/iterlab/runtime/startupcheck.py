"""Noticing that `on_startup` has changed since it last ran.

`on_startup` is the one handler that does not take effect on the next click,
because it does not run on the next click — it ran once, when the session began.
So an edit to it is silent: the researcher changes how their data loads, clicks
something, and nothing whatsoever happens. Nothing is broken, so no fault is
reported; the code simply never runs. That silence is the same failure mode the
project treats as serious everywhere else, and it deserves the same treatment.

What counts as "changed" is deliberately narrower than "the file changed", or
every edit to any handler would claim startup was stale. It is also deliberately
wider than "the text of `on_startup` changed", because startup's behaviour lives
partly in the module-level helpers it calls:

    def _load(path):            # editing this changes what startup does
        return np.loadtxt(path)

    def on_startup(ev):
        ev.data = _load("huge.csv")

So the fingerprint covers `on_startup` plus every module-level function
reachable from it. Comparison is over the parsed structure rather than the text,
so reformatting and comments do not raise a false alarm.

No GUI imports.
"""

from __future__ import annotations

import ast
import hashlib

from ..codegen.templates import read_source

STARTUP = "on_startup"


def _module_functions(tree):
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _called_names(node):
    """Every plain name called inside this function.

    Attribute calls (`np.loadtxt`, `ev.spectrum.plot`) are ignored: they belong
    to imported libraries or to element handles, neither of which lives in this
    file, so neither can be edited into staleness here.
    """
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            names.add(child.func.id)
    return names


def _reachable(functions, root):
    """`root` plus every module-level function it can reach, transitively."""
    seen = []
    pending = [root]
    while pending:
        name = pending.pop()
        if name in seen or name not in functions:
            continue
        seen.append(name)
        pending.extend(sorted(_called_names(functions[name])))
    return seen


def fingerprint(code_path):
    """A stable hash of the startup behaviour defined in this file.

    Returns None when there is nothing to fingerprint — no `on_startup`, or a
    file that will not parse. None never compares equal to a real fingerprint,
    and two Nones compare equal, so a broken file mid-edit raises no alarm and a
    file that never had a startup raises none either.
    """
    try:
        tree = ast.parse(read_source(code_path))
    except (SyntaxError, ValueError, OSError):
        # A file being typed into is not a file that changed its startup. The
        # next successful parse settles it.
        return None

    functions = _module_functions(tree)
    if STARTUP not in functions:
        return None

    digest = hashlib.sha256()
    for name in sorted(_reachable(functions, STARTUP)):
        digest.update(ast.dump(functions[name]).encode("utf-8"))
    return digest.hexdigest()
