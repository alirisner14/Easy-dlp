"""A course is not only its videos.

Most lessons attach something - a worksheet, a brush set, a project file - and
collecting those by hand is the same tedium the page scanner was written to
end. Two things have to hold for that to be safe: only links the page plainly
offers as downloads are picked up, and a handout is fetched as the file it is
rather than run through the video machinery, which would either do nothing or
corrupt it.
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import downloader as D, pagescan

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


PAGE = """
<link rel="canonical" href="https://school.example.com/lessons/12">
<a href="/uploads/Character-Worksheet.pdf"><p>Character worksheet</p></a>
<a href="/files/brushes.brushset" download="MyBrushes.brushset">Download</a>
<a class="btn" href="/dl/pack.zip">Project files</a>
<a href="/img/reference-sheet.jpg" download>Download reference</a>
<a href="/img/logo.png">Home</a>
<a href="/avatars/tutor.jpg"><img src="/avatars/tutor.jpg"></a>
<a href="/lessons/13">Next lesson</a>
<a href="https://twitter.com/someone">Follow along</a>
<a href="/uploads/Character-Worksheet.pdf">Worksheet</a>
"""

print("1. the handouts on a lesson page, and nothing else", flush=True)
rows = pagescan.resources_from_page(PAGE)
names = [n for _u, n in rows]
urls = [u for u, _n in rows]
ok(len(rows) == 4, "four downloads found, not ten links (%d)" % len(rows))
ok("CharacterWorksheet.pdf" in names, "the worksheet, named from its link (%s)" % names)
ok("MyBrushes.brushset" in names, "a download attribute names the brush set")
ok("ProjectFiles.zip" in names, "an ordinary link to a zip counts as well")
ok("DownloadReference.jpg" in names, "an image the page offers to download")
ok(not any("logo" in u for u in urls), "the site's logo is left alone")
ok(not any("avatar" in u for u in urls), "so is somebody's avatar")
ok(not any("twitter" in u for u in urls), "and a link to another site")
ok(len(set(urls)) == len(urls), "the same file listed twice is staged once")
ok(all(u.startswith("https://school.example.com/") for u in urls),
   "relative links are made whole from the page's own address")

print("2. nothing is invented where there is nothing to find", flush=True)
ok(pagescan.resources_from_page("") == [], "empty text")
ok(pagescan.resources_from_page("<a href='/about'>About</a>") == [], "an ordinary page")
ok(pagescan.resources_from_page('<a href="/a/x.pdf">Sheet</a>') == [],
   "a relative link with no address to resolve it against is skipped, "
   "rather than staged as a row that cannot work")
ok(pagescan.resources_from_page('<a href="javascript:save()">Download</a>') == [],
   "a script link is not a file")

print("3. telling a handout from a video", flush=True)
ok(D.resource_ext("https://x.com/a/Worksheet.pdf") == "pdf", "by its address")
ok(D.resource_ext("https://x.com/a/sheet.PDF?token=9") == "pdf",
   "case and a query string do not hide it")
ok(D.resource_ext("https://x.com/dl/1234", "1.03_Brushes.brushset") == "brushset",
   "by its name, when the address has no extension of its own")
ok(D.resource_ext("https://vz-x.b-cdn.net/abc/playlist.m3u8") is None,
   "a playlist is still a video")
ok(D.resource_ext("https://x.com/watch?v=abc") is None, "so is an ordinary page")

print("4. the file name keeps its extension", flush=True)
ok(D.resource_template("1.03_Sheet", "pdf") == "1.03_Sheet.pdf", "added when missing")
ok(D.resource_template("1.03_Sheet.pdf", "pdf") == "1.03_Sheet.pdf", "never doubled")
ok(D.resource_template("", "zip", "https://x.com/dl/Project%20Files.zip")
   == "Project Files.zip", "the link names it when nothing else does")
ok(D.resource_template("", "pdf", "https://x.com/dl/") == "Resource.pdf",
   "and there is always some name")

print("5. a worksheet is fetched as a file, not as a video", flush=True)
engine = D.Engine()
engine._stop = True
engine.exe = "yt-dlp"
opts = {"outdir": ".", "quality": "Audio only", "container": "mkv",
        "thumbnail": True, "metadata": True, "subtitles": True,
        "sponsorblock": True, "rate_limit": "4M", "cookies_file": ""}
job = engine.add("https://school.example.com/uploads/sheet.pdf", opts,
                 name="1.03_CharacterWorksheet")
args = engine.build_args(job)
for flag in ("-x", "--embed-thumbnail", "--embed-metadata", "--write-subs",
             "--merge-output-format", "--sponsorblock-remove"):
    ok(flag not in args, "%s would do nothing here, or damage the file" % flag)
ok(args[args.index("-o") + 1] == "1.03_CharacterWorksheet.pdf",
   "it lands under the name it was staged with, extension and all")
ok("-r" in args and args[args.index("-r") + 1] == "4M",
   "a speed limit still applies - it is the same connection")
ok(args[-1] == job.url, "the address comes last, as yt-dlp expects")

print("6. videos are untouched by any of this", flush=True)
video = engine.add("https://vz-x.b-cdn.net/abc/playlist.m3u8",
                   {"outdir": ".", "quality": "1080p", "container": "mp4",
                    "thumbnail": True, "metadata": True}, name="1.04_Lesson")
args = engine.build_args(video)
ok(args[args.index("-o") + 1] == "1.04_Lesson.%(ext)s", "still named by yt-dlp")
ok("--embed-thumbnail" in args, "and still gets its cover image")
ok("--merge-output-format" in args, "and its container")
ok("--extractor-args" in args, "both paths still get past Cloudflare")
engine.shutdown()

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
