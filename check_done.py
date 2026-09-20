"""Do the finished jobs actually have a finished file on the other end?

A job is marked Done when yt-dlp exits cleanly, but the last step is a copy
across to the download folder. If that was interrupted the row still reads
Done while the file is missing or half written.

    python check_done.py [download folder]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evd import paths

outdir = paths.download_dir()
rows = json.load(open(paths.queue_file(), encoding="utf-8"))
done = [r for r in rows if r.get("status") == "Done"]

print("download folder: %s" % outdir, flush=True)
print("jobs marked Done: %d\n" % len(done), flush=True)

for row in done:
    name = row.get("name") or row.get("title") or "?"
    path = row.get("filepath") or ""
    if not path:
        print("  %-50s NO FILE PATH RECORDED" % name[:50], flush=True)
        continue
    try:
        mb = os.path.getsize(path) / 1024 / 1024
        verdict = "ok" if mb > 1 else "SUSPICIOUSLY SMALL"
        print("  %-50s %8.1f MB  %s" % (name[:50], mb, verdict), flush=True)
    except OSError as exc:
        print("  %-50s MISSING (%s)" % (name[:50], exc.__class__.__name__), flush=True)

print("\nanything unfinished sitting in the folder:", flush=True)
found = 0
try:
    names = sorted(os.listdir(outdir))
except OSError as exc:
    raise SystemExit("cannot read %s: %s" % (outdir, exc))
for name in names:
    path = os.path.join(outdir, name)
    if not os.path.isfile(path):
        continue
    mb = os.path.getsize(path) / 1024 / 1024
    if name.endswith((".temp.mp4", ".part", ".tmp")) or ".part-Frag" in name \
            or (name.endswith(".mp4") and mb < 5):
        print("  %-56s %7.1f MB" % (name[:56], mb), flush=True)
        found += 1
print("  none" if not found else "  (%d worth a look)" % found, flush=True)
