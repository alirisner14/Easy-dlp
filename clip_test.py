"""Part of a video, rather than all of it.

Fetching a two-hour recording to keep five minutes of it, then trimming in
another program, is the slow way round. A range typed after the link -
"https://... 1:30-5:00" - asks yt-dlp for that stretch only.

The things that must hold: ranges read the way people type them, a range
that makes no sense is caught rather than quietly ignored (which would mean
downloading the whole video), a clip never shares a file name with the full
video, and the range survives a restart.
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


URL = "https://vz-x.b-cdn.net/abc/playlist.m3u8"

print("1. ranges read the way people type them", flush=True)
for typed, want in [
    ("1:30-5:00", "90-300"),
    ("0:20-0:30", "20-30"),
    ("1:02:03-1:05:00", "3723-3900"),
    ("90-300", "90-300"),
    ("1:30 - 5:00", "90-300"),
    ("[1:30-5:00]", "90-300"),
    ("1:30 to 5:00", "90-300"),
    ("1:30–5:00", "90-300"),           # an en dash, as phones type it
    ("1:30-", "90-inf"),
    ("1:30-end", "90-inf"),
    ("-5:00", "0-300"),
]:
    ok(D.parse_section(typed) == want, "%-18r -> %s (%s)" % (typed, want, D.parse_section(typed)))

print("2. nonsense is refused, not guessed at", flush=True)
for typed in ("5:00-1:30", "1:30-1:30", "abc-def", "-", "", "1:30", "lesson 2"):
    ok(D.parse_section(typed) is None, "%r is not a usable range" % typed)

print("3. the range comes off the end of the URL box", flush=True)
link, section = D.split_section(URL + " 1:30-5:00")
ok(link == URL and section == "90-300", "link and range separated (%r, %r)" % (link, section))
link, section = D.split_section(URL)
ok(link == URL and section == "", "no range, the link comes back whole")
link, section = D.split_section("https://example.com/watch?t=1-2&v=x")
ok(section == "", "a dash inside a URL is not a range")
ok(D.looks_like_range(URL + " 5:00-1:30") and D.split_section(URL + " 5:00-1:30")[1] == "",
   "a backwards range is spotted as a range, and refused - so the row can "
   "be held back instead of downloading the whole video")
ok(not D.looks_like_range(URL), "and a plain link is not mistaken for one")

print("4. a pasted list can carry ranges", flush=True)
rows = D.parse_entries(URL + " | 2.05_ColourTheory | 1:30-5:00\n"
                       + URL.replace("abc", "def") + " | 2.06_Shading")
ok(len(rows) == 2, "both rows read")
ok(rows[0] == (URL + " 1:30-5:00", "2.05_ColourTheory"),
   "the range rides along with the link, as it would be typed (%r)" % (rows[0],))
ok(rows[1][1] == "2.06_Shading" and " " not in rows[1][0],
   "a row without one is untouched")
rows = D.parse_entries(URL + " | Part 1 | Intro")
ok(rows[0] == (URL, "Part 1 | Intro"),
   "a name with a pipe in it is not mistaken for a range")

print("5. yt-dlp is asked for the range, and the file says which part", flush=True)
engine = D.Engine()
engine._stop = True
engine.exe = "yt-dlp"
job = engine.add(URL, {"outdir": "."}, name="2.05_ColourTheory", section="90-300")
args = engine.build_args(job)
ok("--download-sections" in args
   and args[args.index("--download-sections") + 1] == "*90-300",
   "--download-sections *90-300 is passed")
template = args[args.index("-o") + 1]
ok(template == "2.05_ColourTheory (1m30s-5m00s).%(ext)s",
   "named so it cannot collide with the full video (%s)" % template)
ok(job.label.endswith("(1m30s-5m00s)"), "and the queue row says so too")

open_ended = engine.add(URL, {"outdir": "."}, name="Talk", section="3723-inf")
args = engine.build_args(open_ended)
ok(args[args.index("--download-sections") + 1] == "*3723-inf", "to the end works")
ok(args[args.index("-o") + 1] == "Talk (1h02m03s-end).%(ext)s",
   "and hours are spelled out in the name")

whole = engine.add(URL, {"outdir": "."}, name="2.05_ColourTheory")
args = engine.build_args(whole)
ok("--download-sections" not in args, "a whole video is not given a range")
ok(args[args.index("-o") + 1] == "2.05_ColourTheory.%(ext)s", "nor a suffix")

handout = engine.add("https://x.com/sheet.pdf", {"outdir": "."}, name="Sheet",
                     section="90-300")
ok("--download-sections" not in engine.build_args(handout),
   "a handout ignores a range - there is no such thing as part of a pdf")

print("6. a clip is still a clip after a restart", flush=True)
saved = engine.export_jobs()
again = D.Engine()
again._stop = True
again.import_jobs(saved)
restored = [j for j in again.all_jobs() if j.name == "2.05_ColourTheory" and j.section]
ok(restored and restored[0].section == "90-300",
   "the range is kept in the saved queue")
ok(any(j.name == "2.05_ColourTheory" and not j.section for j in again.all_jobs()),
   "and the whole-video job stays whole")
engine.shutdown()
again.shutdown()

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
