"""The version number lives in more than one place, so the places must agree.

`evd/__init__.py` is what the application reports, the changelog heading is
what a customer reads, and the git tag is what a release is cut from. Three
copies of one fact drift apart eventually, and the way you find out is a
support email about a version that does not exist.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ROOT)
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import __version__ as code

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## (\d+\.\d+\.\d+) - (\d{4}-\d{2}-\d{2})\s*$", re.M)


def git(*args):
    try:
        out = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


print("1. the number itself", flush=True)
ok(SEMVER.match(code), "evd/__init__.py is a semantic version (%s)" % code)

print("2. the changelog agrees", flush=True)
with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
    changelog = fh.read()
entries = HEADING.findall(changelog)
ok(bool(entries), "the changelog has dated version headings (%d)" % len(entries))
if entries:
    newest, when = entries[0]
    ok(newest == code,
       "its newest entry is the version in the code (%s vs %s)" % (newest, code))
    ok(len(entries) == len(set(v for v, _d in entries)),
       "no version is listed twice")
    ordered = sorted(entries, key=lambda e: [int(n) for n in e[0].split(".")],
                     reverse=True)
    ok([v for v, _d in entries] == [v for v, _d in ordered],
       "newest first, as the file says it is")

print("3. the release is described before it is cut", flush=True)
body = changelog.split("## " + code, 1)[-1].split("\n## ", 1)[0]
ok(len(body.strip()) > 200,
   "this version's entry actually says what changed (%d characters)"
   % len(body.strip()))

print("4. the tag agrees, once there is one", flush=True)
tags = [t for t in git("tag", "--list", "v*").splitlines() if SEMVER.match(t[1:])]
if not tags:
    print("     no tags yet - nothing released, so nothing to disagree with",
          flush=True)
else:
    newest_tag = max(tags, key=lambda t: [int(n) for n in t[1:].split(".")])
    ok(newest_tag[1:] == code,
       "the newest tag is this version (%s vs %s)" % (newest_tag, code))
    ok(("v" + code) in tags or newest_tag[1:] == code,
       "this version is tagged, or is the one being prepared")

print("5. the documents do not name a stale version", flush=True)
# Only where a number is plainly this product's version. A bare "10.2.4" in
# prose is a Microsoft Store policy number, not a release of ours.
IN_CONTEXT = re.compile(
    r"(?:Easy-dlp[- ]Setup[- ]|AppVersion=|OutputBaseFilename=Easy-dlp-Setup-"
    r"|[Vv]ersion[: ]+)(\d+\.\d+\.\d+)")
stale = []
for rel in ("RELEASING.md", "legal/direct/INSTALL.md", "README.md"):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        continue
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            for found in IN_CONTEXT.findall(line):
                if found != code:
                    stale.append("%s:%d says %s" % (rel, n, found))
ok(not stale, "no document names a version that is not %s%s"
   % (code, "" if not stale else " - " + "; ".join(stale[:4])))

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
