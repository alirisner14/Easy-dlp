"""A restart must keep the part-downloaded fragments, not throw them away.

The scratch folder is named after the job id, so if a restored job is given
a fresh id it silently loses hours of downloading and starts the video from
the beginning.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


print("1. a job part way through, then the app restarts", flush=True)
first = D.Engine()
first._stop = True
job = first.add("https://example.com/big.m3u8", {"outdir": "."}, name="4.10_Part1")
job.status = D.PAUSED
job.pct = 0.61

work = D.job_work_dir(job.id)
with open(os.path.join(work, "big.mp4.part"), "wb") as fh:
    fh.write(b"x" * 4096)                      # what it already downloaded
ok(os.path.isdir(work), "it has a scratch folder with its progress in it")

rows = first.export_jobs()
ok(any(r.get("id") for r in rows), "the saved queue records the job id")

second = D.Engine()                            # a fresh session
second._stop = True
second.import_jobs(json.loads(json.dumps(rows)))
back = second.all_jobs()[0]
ok(len(second.all_jobs()) == 1, "the job came back")
ok(back.id == job.id, "under the same id (%s vs %s)" % (back.id, job.id))
ok(D.job_work_dir(back.id) == work, "so it points at the same scratch folder")
ok(os.path.exists(os.path.join(D.job_work_dir(back.id), "big.mp4.part")),
   "and its part-downloaded file is still there to carry on from")
ok(round(back.pct, 2) == 0.61, "progress shown matches what is on disk (%.0f%%)"
   % (back.pct * 100))

print("2. the queue is still coherent afterwards", flush=True)
ok(second.order == [job.id], "the order list uses the restored id (%r)" % second.order)
ok(list(second.jobs) == [job.id], "and so does the job table")
ok(second.get(job.id) is back, "lookups by that id find the job")
second.touch(job.id)
ok(job.id in second.dirty, "the view is told to redraw it")

print("3. two sessions restoring the same file do not collide", flush=True)
third = D.Engine()
third._stop = True
third.import_jobs(json.loads(json.dumps(rows)))
third.import_jobs(json.loads(json.dumps(rows)))   # same rows twice
ids = [j.id for j in third.all_jobs()]
ok(len(ids) == len(set(ids)), "every job still has a unique id (%d jobs)" % len(ids))

shutil.rmtree(work, ignore_errors=True)
print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
