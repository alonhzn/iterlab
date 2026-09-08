"""Check that every external link in README.md actually resolves.

PyPI renders README.md on its own page, anonymously. A link that works for the
repository owner in a browser - because they are signed in and the repository is
private - is a 404 to everyone arriving at the project for the first time, and
the logo is a broken image. Neither is visible from here: the page looks right
to whoever published it.

So this asks the way a stranger's browser would, with no credentials at all:

    python tools/check_readme_links.py

Run it after making the repository public and before publishing. A non-zero exit
means at least one link would be dead on PyPI.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"

#: Matches both markdown links and the src of an HTML img tag.
LINK = re.compile(r'(?:\]\(|src=")(https?://[^\s")]+)')

TIMEOUT = 20


def links(text):
    return sorted(set(LINK.findall(text)))


def check(url):
    """(ok, detail). Anonymous on purpose: that is who reads a PyPI page."""
    request = urllib.request.Request(url, headers={"User-Agent": "iterlab-link-check"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return True, f"{response.status} {response.headers.get('Content-Type', '')}"
    except urllib.error.HTTPError as exc:
        hint = ""
        if exc.code == 404 and "github" in url:
            # By far the likeliest cause, and the one that is invisible to the
            # person who owns the repository.
            hint = "  <- private repository? raw links 404 without a token"
        return False, f"HTTP {exc.code}{hint}"
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        return False, f"{type(exc).__name__}: {exc}"


def main():
    found = links(README.read_text(encoding="utf-8"))
    if not found:
        print("no external links in README.md")
        return 0

    failures = 0
    for url in found:
        ok, detail = check(url)
        print(f"{'OK  ' if ok else 'DEAD'}  {url}\n        {detail}")
        failures += not ok

    print()
    if failures:
        print(f"{failures} of {len(found)} links would be dead on the PyPI page.")
        return 1
    print(f"all {len(found)} links resolve anonymously.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
