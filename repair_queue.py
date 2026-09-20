"""Reunite the saved queue with the fragments already on disk.

Each scratch folder is named after its job id and holds a file named after
the video. A queue saved before ids were recorded - or edited by hand - can
be matched back up, so part-finished videos carry on instead of starting
again.

Dry run by default:

    python repair_queue.py            # report only
    python repair_queue.py --apply    # write queue.json
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evd import paths

QUEUE = paths.queue_file()
WORK = paths.work_root()
BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "EVD-queue-backup")
apply_it = "--apply" in sys.argv


def biggest_file(folder):
    best, size = None, 0
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if os.path.isfile(path) and os.path.getsize(path) > size:
                best, size = name, os.path.getsize(path)
        except OSError:
            pass
    return best, size


on_disk = {}
for entry in os.listdir(WORK):
    folder = os.path.join(WORK, entry)
    if not os.path.isdir(folder):
        continue
    name, size = biggest_file(folder)
    if name and size > 1024 * 1024:
        stem = name.split(".mp4")[0].split(".part")[0]
        on_disk[stem] = (entry, size)

print("scratch folders holding real data: %d" % len(on_disk), flush=True)
rows = json.load(open(QUEUE, encoding="utf-8"))
print("queue rows: %d\n" % len(rows), flush=True)

matched = 0
for row in rows:
    if row.get("id"):
        continue
    name = row.get("name") or ""
    hit = on_disk.get(name)
    if not hit and name:
        hit = next((v for k, v in on_disk.items() if k.startswith(name[:24])), None)
    if hit:
        row["id"] = hit[0]
        matched += 1
        print("  matched %-44s -> %s (%.0f MB kept)"
              % (name[:44], hit[0], hit[1] / 1024 / 1024), flush=True)

kept = sum(v[1] for v in on_disk.values()) / 1024 / 1024 / 1024
print("\nrows given their folder back: %d of %d" % (matched, len(rows)), flush=True)
print("downloading saved if applied: about %.1f GB" % kept, flush=True)

if not apply_it:
    print("\nDRY RUN - nothing written. Re-run with --apply.", flush=True)
    raise SystemExit(0)

os.makedirs(BACKUP_DIR, exist_ok=True)
shutil.copy2(QUEUE, os.path.join(
    BACKUP_DIR, "queue-before-repair-%s.json" % time.strftime("%H%M%S")))
with open(QUEUE, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
print("\nwritten. the previous file was copied to %s" % BACKUP_DIR, flush=True)
