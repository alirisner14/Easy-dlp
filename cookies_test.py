"""Signing in with an exported cookies.txt.

Recent Chrome encrypts its cookie store, so --cookies-from-browser fails and
a membership site redirects to its login page. A cookies.txt exported from
the browser is the way in, and it has to win over the browser setting.
"""
import os
import sys
import tempfile

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from evd import downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


engine = D.Engine()
engine._stop = True
engine.exe = "yt-dlp"

jar = os.path.join(tempfile.gettempdir(), "evd-test-cookies.txt")
with open(jar, "w", encoding="utf-8") as fh:
    fh.write("# Netscape HTTP Cookie File\n")

print("1. the file is offered and used", flush=True)
ok(D.COOKIE_FILE_CHOICE in D.COOKIE_SOURCES, "it appears in the list of sources")
job = engine.add("https://example.com/lesson", {"outdir": ".", "cookies_file": jar})
args = engine.build_args(job)
ok("--cookies" in args, "yt-dlp is told to use a cookie file")
ok(args[args.index("--cookies") + 1] == jar, "and pointed at the chosen one")
ok("--cookies-from-browser" not in args, "the browser is not consulted as well")

print("2. the file wins over a browser setting", flush=True)
job = engine.add("https://example.com/lesson",
                 {"outdir": ".", "cookies": "chrome", "cookies_file": jar})
args = engine.build_args(job)
ok("--cookies" in args and "--cookies-from-browser" not in args,
   "the file is preferred, because reading Chrome no longer works")

print("3. a browser still works when no file is set", flush=True)
job = engine.add("https://example.com/lesson", {"outdir": ".", "cookies": "firefox"})
args = engine.build_args(job)
ok("--cookies-from-browser" in args, "the browser option is still honoured")
ok(args[args.index("--cookies-from-browser") + 1] == "firefox", "with the right browser")

print("4. a path that is not there is ignored rather than breaking the run", flush=True)
job = engine.add("https://example.com/lesson",
                 {"outdir": ".", "cookies": "chrome", "cookies_file": jar + ".gone"})
args = engine.build_args(job)
ok("--cookies" not in args, "no cookie file argument for a missing file")
ok("--cookies-from-browser" in args, "it falls back to the browser setting")

print("5. sites behind Cloudflare are not refused outright", flush=True)
job = engine.add("https://example.com/lesson", {"outdir": "."})
args = engine.build_args(job)
ok("--extractor-args" in args, "the impersonation argument is passed")
ok("generic:impersonate" in args, "aimed at the generic extractor only")

print("6. nothing changed for an ordinary link", flush=True)
job = engine.add("https://vz-abc.b-cdn.net/1234/720p/video.m3u8", {"outdir": "."})
args = engine.build_args(job)
ok(args[-1].endswith("video.m3u8"), "the url is still the last argument")
ok("--cookies" not in args, "and no cookies are sent where none were asked for")

os.remove(jar)
print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
