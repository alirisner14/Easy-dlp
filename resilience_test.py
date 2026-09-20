"""One bad moment must not cost the session.

The heartbeat re-arms itself on its last line, so anything that threw inside
it used to stop it for good: no saves, no progress, and a queue that looked
empty because it was never redrawn - while the window still answered, which
is what made it so hard to spot. Closing had the same shape: one failing step
skipped the rest, including the queue.

Run with APPDATA pointed at a scratch folder.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from evd import config, downloader as D
from evd.ui import App

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


config.save_queue([{"url": "https://example.com/a.m3u8", "name": "01_First",
                    "status": "Paused", "opts": {"outdir": "."}, "id": "aaaaaaaaaaaa"},
                   {"url": "https://example.com/b.m3u8", "name": "02_Second",
                    "status": "Queued", "opts": {"outdir": "."}, "id": "bbbbbbbbbbbb"}])
cfg = config.load()
cfg["staged"] = []
config.save(cfg)

app = App()
app.root.update()
ok(len(app.engine.all_jobs()) == 2, "the saved queue came back (%d)"
   % len(app.engine.all_jobs()))

print("1. a failure inside the heartbeat does not stop it", flush=True)
ticks = {"n": 0}
real_stats = app.update_stats


def exploding_stats():
    ticks["n"] += 1
    if ticks["n"] <= 2:
        raise RuntimeError("pretend the queue drawing blew up")
    return real_stats()


app.update_stats = exploding_stats
for _ in range(40):
    app.root.update()
    app.root.after(60)
ok(ticks["n"] > 5, "the heartbeat kept beating after throwing (%d beats)" % ticks["n"])
ok(app._tick_failures >= 1, "and it counted the failures (%d)" % app._tick_failures)
ok(getattr(app, "_tick_after", None), "the timer is still armed")
app.update_stats = real_stats

print("2. it says so in the log rather than failing silently", flush=True)
log = D.ACTIVITY_LOG.read_text(encoding="utf-8", errors="replace")
ok("display update failed" in log, "the failure is recorded in the activity log")
ok("opened: 2 of 2 saved jobs restored" in log,
   "and opening records what was restored")

print("3. the autosave still runs afterwards", flush=True)
config.save_queue([])
for _ in range(60):
    app.root.update()
    app.root.after(60)
ok(len(config.load_queue()) == 2, "the queue was written again (%d rows)"
   % len(config.load_queue()))

print("4. closing saves the queue even when another step fails", flush=True)
config.save_queue([])


def broken_capture():
    raise RuntimeError("pretend reading the staged boxes blew up")


app._capture_stage = broken_capture
try:
    app.close()
    closed = True
except Exception:
    traceback.print_exc()
    closed = False
ok(closed, "close finished instead of throwing")
saved = config.load_queue()
ok(len(saved) == 2, "the queue was still saved (%d rows)" % len(saved))
ok(all(r.get("id") for r in saved), "with the ids that find part-downloaded files")

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
