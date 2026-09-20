"""Point failed jobs at the master playlist instead of one fixed resolution.

A link that names a resolution - .../720p/video.m3u8 - only works if the video
was published that way, and many are not: they answer 404 while serving every
size, that one included, from the master playlist. Jobs that failed for that
reason can be repaired in place and retried, rather than staged again by hand.

    python fix_resolution_urls.py            # report only
    python fix_resolution_urls.py --apply    # rewrite queue.json
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evd import downloader as D, paths

QUEUE = paths.queue_file()
BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "EVD-queue-backup")
apply_it = "--apply" in sys.argv

rows = json.load(open(QUEUE, encoding="utf-8"))
print("queue holds %d jobs\n" % len(rows), flush=True)

changed = 0
for row in rows:
    master = D.master_playlist(row.get("url") or "")
    if not master:
        continue
    failed = row.get("status") in ("Failed", "Canceled") or "404" in (row.get("error") or "")
    mark = "will retry" if failed else "queued anyway"
    print("  %-46s %s" % ((row.get("name") or "?")[:46], mark), flush=True)
    row["url"] = master
    if failed:
        row["status"] = "Queued"
        row["error"] = ""
        row["pct"] = 0.0
    changed += 1

print("\n%d of %d jobs point at one fixed resolution" % (changed, len(rows)), flush=True)
if not changed:
    raise SystemExit(0)
if not apply_it:
    print("DRY RUN - nothing written. Re-run with --apply, "
          "with the app closed so it does not save over it.", flush=True)
    raise SystemExit(0)

os.makedirs(BACKUP_DIR, exist_ok=True)
shutil.copy2(QUEUE, os.path.join(BACKUP_DIR, "queue-before-urlfix-%s.json"
                                 % time.strftime("%H%M%S")))
with open(QUEUE, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
print("written. the previous file was copied to %s" % BACKUP_DIR, flush=True)
print("Open the app and press Start; the repaired jobs are queued.", flush=True)
