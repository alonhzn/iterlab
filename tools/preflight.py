"""Everything that must be true before publishing, checked in one command.

    python tools/preflight.py

The constitution puts this plainly: "A published version cannot be withdrawn in
any meaningful sense ... The pre-publish gate is the only point at which
enforcement is still possible, so it is absolute rather than advisory."

It was advisory in practice, because nothing enforced it. 1.2.0 and 1.3.0 were
both prepared and handed over while CI had been failing on Linux since 1.2.0 —
the local suite was green on Windows every time, and nobody looked at the run
that tests the platform the developer is not using. That is exactly the gap CI
exists to cover, and exactly the gap a person is worst at closing from memory.

So this asks the questions instead of trusting that they were asked. A non-zero
exit means do not upload.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"


def _run(*args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def declared_version() -> str:
    text = (ROOT / "src" / "iterlab" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "?"


# -- the checks ------------------------------------------------------------


def check_tree_clean():
    code, out, _ = _run("git", "status", "--porcelain")
    if code != 0:
        return FAIL, "git status failed"
    if out:
        return FAIL, f"uncommitted changes:\n        " + "\n        ".join(out.splitlines()[:6])
    return PASS, "working tree clean"


def check_pushed():
    code, out, _ = _run("git", "status", "-sb")
    if code != 0:
        return FAIL, "git status failed"
    line = out.splitlines()[0] if out else ""
    if "[ahead" in line or "[behind" in line:
        return FAIL, f"local and remote differ: {line}"
    return PASS, "commit is on the remote"


def check_ci():
    """The one that was missed. CI must be green for *this* commit."""
    code, sha, _ = _run("git", "rev-parse", "HEAD")
    if code != 0:
        return FAIL, "cannot resolve HEAD"

    code, out, err = _run(
        "gh", "run", "list", "--commit", sha, "--json",
        "conclusion,status,workflowName,url", "--limit", "10",
    )
    if code != 0:
        return WARN, f"could not ask GitHub ({err.splitlines()[0] if err else 'gh failed'})"
    try:
        runs = json.loads(out or "[]")
    except json.JSONDecodeError:
        return WARN, "could not read the GitHub response"

    if not runs:
        return FAIL, f"no CI run for {sha[:8]} yet — push, wait for it, then re-run this"
    unfinished = [r for r in runs if r.get("status") != "completed"]
    if unfinished:
        return FAIL, f"CI still running for {sha[:8]}: {unfinished[0].get('url', '')}"
    failed = [r for r in runs if r.get("conclusion") != "success"]
    if failed:
        detail = ", ".join(f"{r['workflowName']}={r['conclusion']}" for r in failed)
        return FAIL, f"CI is not green for {sha[:8]}: {detail}\n        {failed[0].get('url', '')}"
    return PASS, f"CI green for {sha[:8]} ({len(runs)} workflow(s))"


def check_artifacts():
    version = declared_version()
    dist = ROOT / "dist"
    if not dist.is_dir():
        return FAIL, "no dist/ directory — build first"
    built = sorted(p.name for p in dist.glob(f"iterlab-{version}*"))
    if len(built) < 2:
        return FAIL, f"dist/ has no wheel+sdist for {version}: {built or 'nothing'}"
    stale = [p.name for p in dist.glob("iterlab-*") if f"-{version}" not in p.name]
    if stale:
        return FAIL, f"dist/ also holds other versions, which upload would publish: {stale}"
    return PASS, f"{version}: {', '.join(built)}"


def check_twine():
    code, out, err = _run(sys.executable, "-m", "twine", "check", "dist/*")
    combined = f"{out}\n{err}"
    if code != 0 or "FAILED" in combined:
        return FAIL, "twine check failed"
    return PASS, "twine check passed"


def check_readme_links():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    urls = sorted(set(re.findall(r'(?:\]\(|src=")(https?://[^\s")]+)', text)))
    dead = []
    for url in urls:
        request = urllib.request.Request(url, headers={"User-Agent": "iterlab-preflight"})
        try:
            urllib.request.urlopen(request, timeout=20)
        except Exception:
            dead.append(url)
    if dead:
        return FAIL, f"README links dead for anyone but you: {dead}"
    return PASS, f"all {len(urls)} README links resolve anonymously"


def check_gate_two():
    """Warned about rather than enforced, and the reason is stated.

    The constitution requires a recorded manual pass before each release. Only a
    person can do it, so a tool can ask whether it happened but cannot do it or
    honestly refuse on its behalf.
    """
    version = declared_version()
    text = (ROOT / "VERIFICATION.md").read_text(encoding="utf-8")
    if version in text:
        return PASS, f"VERIFICATION.md mentions {version}"
    return WARN, (
        f"no recorded Gate 2 pass for {version}. The constitution: "
        '"A pass that was not recorded did not happen."'
    )


CHECKS = (
    ("working tree", check_tree_clean),
    ("pushed", check_pushed),
    ("continuous integration", check_ci),
    ("artifacts", check_artifacts),
    ("twine", check_twine),
    ("README links", check_readme_links),
    ("manual verification", check_gate_two),
)


def main() -> int:
    print(f"iterlab preflight — version {declared_version()}\n")
    worst = PASS
    for name, check in CHECKS:
        try:
            status, detail = check()
        except Exception as exc:  # noqa: BLE001 - a broken check is a failed check
            status, detail = FAIL, f"the check itself raised: {exc}"
        print(f"  {status:4}  {name}: {detail}")
        if status == FAIL:
            worst = FAIL
        elif status == WARN and worst != FAIL:
            worst = WARN

    print()
    if worst == FAIL:
        print("DO NOT UPLOAD. A published version cannot be withdrawn.")
        return 1
    if worst == WARN:
        print("Nothing blocking, but read the warnings before uploading.")
        return 0
    print("Clear to upload:  py -m twine upload dist/*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
