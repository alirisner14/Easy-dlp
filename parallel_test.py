"""The parallel limit must hold, even when rows are paused mid-launch.

Reproduces what happened overnight: a row paused while its download was
still being prepared (slow network folder) was marked Paused, freeing its
slot, while the worker went on to launch anyway - so nine downloads ran with
the limit set to three.

No real downloads: yt-dlp is replaced with a stand-in that records launches.
"""
import sys
import threading
import time

sys.path.insert(0, ".")
from evd import downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


class FakeProc:
    """Stands in for yt-dlp: stays alive until it is killed or released."""

    _next_pid = 5000

    def __init__(self):
        FakeProc._next_pid += 1
        self.pid = FakeProc._next_pid
        self.done = threading.Event()
        self.returncode = None
        self.stdout = self

    def __iter__(self):
        self.done.wait(20)
        return iter([])

    def poll(self):
        return self.returncode

    def wait(self):
        self.done.wait(20)
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode

    def finish(self, rc=0):
        self.returncode = rc
        self.done.set()


class Harness:
    """An engine whose launches and folder creation we control."""

    def __init__(self, max_parallel=3):
        self.launched = []
        self.live = []
        self.lock = threading.Lock()
        self.block = None              # set to an Event to stall preparation
        self.in_prep = threading.Event()

        self.real_popen = D.subprocess.Popen
        self.real_makedirs = D.os.makedirs
        self.real_kill = D.Engine._kill
        D.subprocess.Popen = self._popen
        D.os.makedirs = self._makedirs
        D.Engine._kill = self._kill

        self.engine = D.Engine()
        self.engine.exe = "yt-dlp"
        self.engine.max_parallel = max_parallel

    def _popen(self, args, **kw):
        proc = FakeProc()
        proc.url = next((a for a in args if "example.com" in str(a)), "?")
        with self.lock:
            self.launched.append(proc)
            self.live.append(proc)
        return proc

    def launched_urls(self):
        with self.lock:
            return [p.url for p in self.launched]

    def _makedirs(self, path, **kw):
        if self.block is not None:
            self.in_prep.set()
            self.block.wait(20)
        return None

    def _kill(engine_self, proc):
        proc.finish(1)

    def peak_live(self):
        with self.lock:
            return len([p for p in self.live if p.returncode is None])

    def stop(self):
        for p in list(self.live):
            p.finish()
        self.engine._stop = True
        D.subprocess.Popen = self.real_popen
        D.os.makedirs = self.real_makedirs
        D.Engine._kill = self.real_kill


print("1. pausing a row while it is still being prepared", flush=True)
h = Harness(max_parallel=1)
h.block = threading.Event()
jobs = [h.engine.add("https://example.com/%d.m3u8" % i, {"outdir": "."}) for i in range(4)]
h.engine.running = True

ok(h.in_prep.wait(5), "a job reached the slow folder step")
victim = next(j for j in h.engine.all_jobs() if j.status == D.RUNNING)
h.engine.pause_job(victim.id)                 # what you did, per row
time.sleep(0.4)
ok(victim.status == D.PAUSED, "the row shows Paused (%s)" % victim.status)
h.block.set()                                 # the folder finally answers
time.sleep(0.8)
ok(victim.url not in h.launched_urls(),
   "the paused row never launched a download of its own")
ok(victim.status == D.PAUSED, "and it stayed Paused (%s)" % victim.status)
ok(h.peak_live() <= 1, "only the one allowed slot is in use (%d)" % h.peak_live())
h.stop()

print("2. the limit holds while rows are paused one by one", flush=True)
h = Harness(max_parallel=3)
h.block = threading.Event()
h.block.set()                                  # preparation is instant now
for i in range(12):
    h.engine.add("https://example.com/v%d.m3u8" % i, {"outdir": "."})
h.engine.running = True

peak = 0
for _ in range(40):
    time.sleep(0.1)
    peak = max(peak, h.peak_live())
    running = [j for j in h.engine.all_jobs() if j.status == D.RUNNING]
    if running:                                # pause them by hand, as you did
        h.engine.pause_job(running[0].id)
ok(peak <= 3, "never more than the 3 allowed ran at once (peak %d)" % peak)
ok(len(h.engine.all_jobs()) == 12, "no jobs went missing")
h.stop()

print("3. the same window, but cancelling instead of pausing", flush=True)
h = Harness(max_parallel=1)
h.block = threading.Event()
h.engine.add("https://example.com/c.m3u8", {"outdir": "."})
h.engine.running = True
ok(h.in_prep.wait(5), "it reached the slow folder step")
victim = next(j for j in h.engine.all_jobs() if j.status == D.RUNNING)
h.engine.cancel(victim.id)
h.block.set()
time.sleep(0.8)
ok(len(h.launched) == 0, "a cancelled row never launches either (%d)" % len(h.launched))
ok(victim.status == D.CANCELED, "and it reads Cancelled (%s)" % victim.status)
h.stop()

print("4. normal running still works", flush=True)
h = Harness(max_parallel=2)
h.block = threading.Event()
h.block.set()
for i in range(3):
    h.engine.add("https://example.com/n%d.m3u8" % i, {"outdir": "."})
h.engine.running = True
time.sleep(0.9)
ok(len(h.launched) == 2, "two started, as the limit allows (%d)" % len(h.launched))
h.launched[0].finish(0)
time.sleep(0.9)
ok(len(h.launched) == 3, "the third started once a slot freed (%d)" % len(h.launched))
h.stop()

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
