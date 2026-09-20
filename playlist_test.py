"""A fixed resolution in the address is a guess, and often a wrong one.

Plenty of videos answer 404 on .../720p/video.m3u8 while serving every size,
720p included, from the master playlist. A whole course failed that way with
"Unable to download webpage: HTTP Error 404" against videos that were there
all along.

So pages are read into master playlist addresses, and a fixed-size link that
someone copied from the network tab is retried against the master before the
job is called failed.
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from evd import downloader as D, pagescan

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


HOST = "vz-bdcee283-989.b-cdn.net"
GUID = "70e90b3b-6de6-4538-b3be-3f9519c198c9"        # one that really 404ed
FIXED = "https://%s/%s/720p/video.m3u8" % (HOST, GUID)
MASTER = "https://%s/%s/playlist.m3u8" % (HOST, GUID)

print("1. a course page yields master playlist addresses", flush=True)
page = ('<a href="/l/1"><span>2.03</span>'
        '<img src="https://%s/%s/thumbnail.jpg"><p>Line Drawing Exercise</p></a>'
        % (HOST, GUID))
rows = pagescan.lessons_from_page(page)
ok(len(rows) == 1, "the lesson was found")
ok(rows[0][0] == MASTER, "and points at the master playlist")
ok("720p" not in rows[0][0], "no resolution is baked into the address")
ok(rows[0][1] == "2.03_LineDrawingExercise", "named as before (%r)" % rows[0][1])

print("2. spotting a fixed-size address", flush=True)
ok(D.master_playlist(FIXED) == MASTER, "a 720p link maps to the master")
ok(D.master_playlist(FIXED.replace("720p", "1080p")) == MASTER, "so does 1080p")
ok(D.master_playlist(MASTER) is None, "a master is left alone, so it cannot loop")
ok(D.master_playlist("https://example.com/720p/video.m3u8") is None,
   "an unrelated host is left alone")
ok(D.master_playlist("") is None and D.master_playlist(None) is None, "and nothing at all")

# --- drive the engine's real failure handling -------------------------------
class FakeProc:
    """yt-dlp that prints one line and exits with a code."""

    def __init__(self, line, rc):
        self.returncode = rc
        self.stdout = iter([line]) if line else iter([])
        self.pid = 4242

    def poll(self):
        return self.returncode

    def wait(self):
        return self.returncode


def run_with(url, line, rc):
    engine = D.Engine()
    engine._stop = True
    engine.exe = "yt-dlp"
    real_popen, real_makedirs = D.subprocess.Popen, D.os.makedirs
    D.subprocess.Popen = lambda *a, **k: FakeProc(line, rc)
    D.os.makedirs = lambda *a, **k: None
    try:
        job = engine.add(url, {"outdir": "."})
        job.status = D.RUNNING
        engine._run(job)          # the real thing, start to finish
        return job
    finally:
        D.subprocess.Popen, D.os.makedirs = real_popen, real_makedirs


NOT_FOUND = "ERROR: [generic] video: Unable to download webpage: HTTP Error 404: Not Found\n"

print("3. a 404 on a fixed size is retried against the master", flush=True)
job = run_with(FIXED, NOT_FOUND, 1)
ok(job.url == MASTER, "the job now points at the master (%s)" % job.url.rsplit('/', 1)[-1])
ok(job.status == D.QUEUED, "and is queued to run again (%s)" % job.status)
ok(not job.error, "with the error cleared, so the row does not read Failed")

print("4. a 404 on the master itself is reported, not retried forever", flush=True)
job = run_with(MASTER, NOT_FOUND, 1)
ok(job.status == D.ERROR, "it is marked Failed (%s)" % job.status)
ok("404" in (job.error or ""), "keeping the reason")

print("5. other failures are untouched by this", flush=True)
job = run_with(FIXED, "ERROR: unsupported url\n", 1)
ok(job.url == FIXED, "a link that failed for another reason is not rewritten")
ok(job.status == D.ERROR, "and still fails (%s)" % job.status)

print("6. a download that works is unaffected", flush=True)
job = run_with(FIXED, "", 0)
ok(job.status == D.DONE, "success is still success (%s)" % job.status)
ok(job.url == FIXED, "and the address is left as it was")

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
