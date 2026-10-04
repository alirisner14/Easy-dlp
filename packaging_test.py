"""A packaged build must bring its own tools.

Someone who downloads the app has no reason to already have yt-dlp and ffmpeg
on their PATH, and "go and install two command line programs first" is not a
product - it is a dead window reading "yt-dlp was not found on PATH". A
release build carries both inside it; a build from source does not, and falls
back to PATH, which is what you want while developing.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


TOOL = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
FFMPEG = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"


class Frozen:
    """Stand in for a one-file build unpacked into a temporary folder."""

    def __init__(self, *names, nested=False):
        self.dir = tempfile.mkdtemp(prefix="evd-frozen-")
        where = os.path.join(self.dir, "tools") if nested else self.dir
        os.makedirs(where, exist_ok=True)
        for name in names:
            with open(os.path.join(where, name), "wb") as fh:
                fh.write(b"MZ")          # enough to be a file

    def __enter__(self):
        self.kept = (getattr(sys, "_MEIPASS", None), getattr(sys, "frozen", False))
        sys._MEIPASS = self.dir
        sys.frozen = True
        return self

    def __exit__(self, *exc):
        # tidy up: every run used to leave a folder behind in %TEMP%
        shutil.rmtree(self.dir, ignore_errors=True)
        meipass, frozen = self.kept
        if meipass is None:
            del sys._MEIPASS
        else:
            sys._MEIPASS = meipass
        sys.frozen = frozen


print("1. a release build finds the tools it carries", flush=True)
with Frozen(TOOL, FFMPEG) as box:
    found = D.find_ytdlp()
    ok(found and os.path.dirname(found) == box.dir,
       "yt-dlp comes from inside the build, not from PATH (%s)" % found)
    ok(D.find_ffmpeg() and os.path.dirname(D.find_ffmpeg()) == box.dir,
       "and so does ffmpeg")

print("2. a tools/ subfolder works as well", flush=True)
with Frozen(TOOL, nested=True) as box:
    found = D.find_ytdlp()
    ok(found and found.endswith(os.path.join("tools", TOOL)),
       "found one level down too (%s)" % found)

print("3. what is bundled beats what is installed", flush=True)
with Frozen(TOOL) as box:
    ok(os.path.dirname(D.find_ytdlp()) == box.dir,
       "a stale copy on PATH does not decide how an install behaves")

print("4. a build from source still uses PATH", flush=True)
ok(D.bundled_tool(TOOL) is None, "nothing is claimed to be bundled when it is not")
ok(D.find_ytdlp() is not None,
   "and yt-dlp is still found the usual way while developing")

print("5. nothing blows up when the tools are simply absent", flush=True)
with Frozen() as box:
    ok(D.find_ytdlp() is None or os.path.dirname(D.find_ytdlp()) != box.dir,
       "an empty build falls through rather than returning a path that is not there")
    ok(D.bundled_tool(TOOL) is None, "and says so plainly")

print("6. the engine passes the bundled ffmpeg on to yt-dlp", flush=True)
with Frozen(TOOL, FFMPEG) as box:
    engine = D.Engine()
    engine._stop = True
    ok(engine.ffmpeg and os.path.dirname(engine.ffmpeg) == box.dir,
       "the engine picked up the bundled one (%s)" % engine.ffmpeg)
    job = engine.add("https://example.com/a.m3u8", {"outdir": "."}, name="One")
    args = engine.build_args(job)
    ok("--ffmpeg-location" in args
       and os.path.dirname(args[args.index("--ffmpeg-location") + 1]) == box.dir,
       "and told yt-dlp where to find it")
    engine.shutdown()

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
