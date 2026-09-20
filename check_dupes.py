"""Is anything still queued already sitting in the download folder?

Lessons downloaded earlier under a different name would otherwise be pulled
a second time. The matching is by name, so read it as a hint rather than a
verdict - parts of one series look alike.

    python check_dupes.py [download folder]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evd import paths

outdir = paths.download_dir()
rows = json.load(open(paths.queue_file(), encoding="utf-8"))

files = {}
for name in os.listdir(outdir):
    path = os.path.join(outdir, name)
    if os.path.isfile(path):
        files[name] = os.path.getsize(path)


def words(text):
    return set(w.lower() for w in re.findall(r"[A-Z][a-z]+|\d+", text) if len(w) > 2)


print("still to download, against what is already there\n", flush=True)
for row in rows:
    if row.get("status") == "Done":
        continue
    name = row.get("name") or "?"
    pct = round((row.get("pct") or 0) * 100)
    mine = words(name)
    note = ""
    exact = next((f for f in files if f.startswith(name)), None)
    if exact:
        mb = files[exact] / 1024 / 1024
        note = ("already there, %.0f MB" % mb if mb > 50
                else "only a %.1f MB stub of it is there" % mb)
    else:
        best, score = None, 0
        for fname in files:
            overlap = len(mine & words(fname))
            if overlap > score:
                best, score = fname, overlap
        if best and score >= 4:
            note = "maybe %s (%.0f MB) - check before trusting this" % (
                best[:40], files[best] / 1024 / 1024)
    print("  %-46s %3d%%  %s" % (name[:46], pct, note), flush=True)
